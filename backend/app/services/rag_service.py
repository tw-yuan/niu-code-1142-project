import json
import time
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import ChatMessage, ChatSession, Document, RAGRetrievedChunk, RAGRun, now_iso
from app.schemas import ChatSessionCreate
from app.services.chroma_service import ChromaService
from app.services.courses_service import CoursesService
from app.services.document_access import DocumentAccessService
from app.services.json_utils import from_json_list, to_json
from app.services.llm_client import LLMClient
from app.services.prompt_loader import load_prompt


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._last_citations: list[dict[str, Any]] = []
        self._last_run_id: str | None = None
        self._last_started_at: float | None = None

    async def create_session(self, user_id: str, body: ChatSessionCreate) -> dict[str, Any]:
        shared_doc_ids = []
        if body.course_id:
            shared_doc_ids = await CoursesService(self.db).course_document_ids(user_id, body.course_id)
            if not set(body.doc_ids).issubset(set(shared_doc_ids)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Selected course documents are no longer available. "
                        "Please refresh the course document selection."
                    ),
                )
        else:
            await self._validate_doc_ids(user_id, body.doc_ids)
        session = ChatSession(
            user_id=user_id,
            title=body.title or "新的對話",
            doc_ids=to_json(body.doc_ids),
            course_id=body.course_id,
            mode=body.mode,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return self._session_out(session)

    async def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        sessions = (
            await self.db.execute(
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(desc(ChatSession.updated_at))
            )
        ).scalars().all()
        return [self._session_out(session) for session in sessions]

    async def get_session_detail(self, user_id: str, session_id: str) -> dict[str, Any]:
        session = await self._get_session(user_id, session_id)
        messages = (
            await self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.created_at)
            )
        ).scalars().all()
        data = self._session_out(session)
        data["messages"] = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "citations": from_json_list(msg.citations),
                "token_count": msg.token_count,
                "created_at": msg.created_at,
            }
            for msg in messages
        ]
        return data

    async def delete_session(self, user_id: str, session_id: str) -> None:
        session = await self._get_session(user_id, session_id)
        await self.db.delete(session)
        await self.db.commit()

    async def stream_answer(self, session_id: str, question: str, user_id: str):
        started_at = time.perf_counter()
        session = await self._get_session(user_id, session_id)
        history = await self._history(session.id)
        doc_ids = from_json_list(session.doc_ids)
        shared_doc_ids = []
        if session.course_id:
            shared_doc_ids = await CoursesService(self.db).course_document_ids(user_id, session.course_id)
        rewritten = await self._rewrite_question(question, history, user_id)
        llm = LLMClient(self.db)
        query_embedding = (await llm.embed([rewritten], user_id=user_id))[0]
        explicit_doc_scope = bool(doc_ids)
        query_doc_ids = doc_ids
        if session.course_id:
            allowed = set(shared_doc_ids)
            query_doc_ids = [doc_id for doc_id in doc_ids if doc_id in allowed]
        if session.course_id and not query_doc_ids and not explicit_doc_scope:
            query_doc_ids = shared_doc_ids
        if session.course_id and not query_doc_ids:
            chunks = []
        else:
            chunks = await ChromaService().query_chunks(
                user_id,
                query_embedding,
                doc_ids=query_doc_ids,
                shared_doc_ids=shared_doc_ids,
                n_results=5,
            )
        context, citations = self._build_context(chunks, set(shared_doc_ids))
        self._last_citations = citations

        prompt_name = {
            "strict": "rag_strict",
            "socratic": "rag_socratic",
        }.get(session.mode, "rag_chat")
        system_prompt, cfg = load_prompt(prompt_name, context=context)
        run = RAGRun(
            user_id=user_id,
            session_id=session.id,
            question=question,
            rewritten_question=rewritten,
            doc_ids=to_json(query_doc_ids),
            mode=session.mode,
            prompt_name=prompt_name,
            context_tokens=max(1, len(context) // 4),
        )
        self.db.add(run)
        await self.db.flush()
        for citation in citations:
            self.db.add(
                RAGRetrievedChunk(
                    run_id=run.id,
                    doc_id=citation.get("doc_id"),
                    filename=citation.get("filename"),
                    page_num=_int_or_none(citation.get("page")),
                    chunk_index=_int_or_none(citation.get("chunk_index")),
                    rank=int(citation.get("index") or 0),
                    distance=_float_or_none(citation.get("distance")),
                    snippet=str(citation.get("snippet") or ""),
                    support_status=str(citation.get("support_status") or "unverified"),
                )
            )
        await self.db.commit()
        self._last_run_id = run.id
        self._last_started_at = started_at

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-8:])
        messages.append({"role": "user", "content": question})

        async for chunk in llm.stream_chat(
            messages,
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
            feature="rag_chat",
            user_id=user_id,
        ):
            yield chunk

    async def save_message(
        self,
        session_id: str,
        user_id: str,
        user_content: str,
        assistant_content: str,
        citations: list[dict[str, Any]],
    ) -> None:
        session = await self._get_session(user_id, session_id)
        self.db.add(ChatMessage(session_id=session.id, role="user", content=user_content))
        self.db.add(
            ChatMessage(
                session_id=session.id,
                role="assistant",
                content=assistant_content,
                citations=to_json(citations),
                token_count=max(1, len(assistant_content) // 4),
            )
        )
        session.updated_at = now_iso()
        if not session.title or session.title == "新的對話":
            session.title = user_content[:40]
        await self.db.commit()

    async def finalize_answer(
        self,
        assistant_content: str,
        citations: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        citations = self._mark_citation_support(citations or self._last_citations, assistant_content)
        if self._last_run_id:
            run = await self.db.get(RAGRun, self._last_run_id)
            if run:
                run.status = "completed"
                run.answer_tokens = max(1, len(assistant_content) // 4)
                run.citation_support_rate = _support_rate(citations)
                run.latency_ms = (
                    int((time.perf_counter() - self._last_started_at) * 1000)
                    if self._last_started_at
                    else None
                )
                run.completed_at = now_iso()
            retrieved = (
                await self.db.execute(
                    select(RAGRetrievedChunk).where(RAGRetrievedChunk.run_id == self._last_run_id)
                )
            ).scalars().all()
            support_by_rank = {
                int(citation["index"]): str(citation.get("support_status") or "unverified")
                for citation in citations
                if citation.get("index") is not None
            }
            for item in retrieved:
                item.support_status = support_by_rank.get(item.rank, item.support_status)
        await self.db.commit()
        return citations

    async def get_last_citations(self) -> list[dict[str, Any]]:
        return self._last_citations

    async def _rewrite_question(
        self, question: str, history: list[dict[str, str]], user_id: str
    ) -> str:
        if not history:
            return question
        llm = LLMClient(self.db)
        prompt = (
            "請把學生最新問題改寫成適合向量檢索的獨立查詢。"
            "只輸出改寫後的查詢，不要解釋。"
        )
        messages = [{"role": "system", "content": prompt}, *history[-4:], {"role": "user", "content": question}]
        rewritten = await llm.chat(messages, temperature=0, max_tokens=160, feature="query_rewrite", user_id=user_id)
        return rewritten.strip() or question

    async def _history(self, session_id: str) -> list[dict[str, str]]:
        rows = (
            await self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(desc(ChatMessage.created_at))
                .limit(10)
            )
        ).scalars().all()
        return [{"role": row.role, "content": row.content} for row in reversed(rows)]

    async def _get_session(self, user_id: str, session_id: str) -> ChatSession:
        session = (
            await self.db.execute(
                select(ChatSession).where(
                    and_(ChatSession.id == session_id, ChatSession.user_id == user_id)
                )
            )
        ).scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
        return session

    async def _validate_doc_ids(
        self,
        user_id: str,
        doc_ids: list[str],
        shared_doc_ids: list[str] | None = None,
    ) -> None:
        if not doc_ids:
            return
        rows = (
            await self.db.execute(
                select(Document.id).where(
                    and_(
                        DocumentAccessService(self.db).accessible_document_condition(user_id),
                        Document.id.in_(doc_ids),
                    )
                )
            )
        ).scalars().all()
        allowed = set(rows) | set(shared_doc_ids or [])
        if not set(doc_ids).issubset(allowed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected documents are no longer available. Please refresh the document selection.",
            )

    def _build_context(
        self,
        chunks: list[dict[str, Any]],
        shared_doc_ids: set[str] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        if not chunks:
            return "目前沒有可用的參考資料。", []
        shared_doc_ids = shared_doc_ids or set()
        parts: list[str] = []
        citations: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks, 1):
            meta = chunk["metadata"]
            parts.append(
                f"[{index}] {meta.get('filename')} 第 {meta.get('page_num')} 頁\n{chunk['text']}"
            )
            citations.append(
                {
                    "index": index,
                    "doc_id": meta.get("doc_id"),
                    "filename": meta.get("filename"),
                    "page": meta.get("page_num"),
                    "chunk_index": meta.get("chunk_index"),
                    "scope": "course" if meta.get("doc_id") in shared_doc_ids else "personal",
                    "distance": chunk.get("distance"),
                    "snippet": _snippet(str(chunk["text"])),
                    "retrieval_score": _score_from_distance(chunk.get("distance")),
                    "support_status": "unverified",
                }
            )
        return "\n\n".join(parts), citations

    def _mark_citation_support(
        self,
        citations: list[dict[str, Any]],
        assistant_content: str,
    ) -> list[dict[str, Any]]:
        normalized_answer = _normalize_text(assistant_content)
        result = []
        for citation in citations:
            snippet = str(citation.get("snippet") or "")
            support_status = "unverified"
            if snippet:
                snippet_words = [word for word in _normalize_text(snippet).split() if len(word) >= 2]
                if snippet_words:
                    matched = sum(1 for word in snippet_words[:30] if word in normalized_answer)
                    ratio = matched / min(len(snippet_words), 30)
                    support_status = "supported" if ratio >= 0.18 else "partial" if ratio >= 0.08 else "unverified"
            result.append({**citation, "support_status": support_status})
        self._last_citations = result
        return result

    def _session_out(self, session: ChatSession) -> dict[str, Any]:
        return {
            "id": session.id,
            "title": session.title,
            "doc_ids": json.loads(session.doc_ids),
            "course_id": session.course_id,
            "mode": session.mode,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }


def _snippet(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


def _score_from_distance(distance: Any) -> float | None:
    value = _float_or_none(distance)
    if value is None:
        return None
    return round(max(0.0, min(1.0, 1.0 - value)), 4)


def _support_rate(citations: list[dict[str, Any]]) -> float | None:
    if not citations:
        return None
    supported = sum(1 for item in citations if item.get("support_status") == "supported")
    return round(supported / len(citations), 4)


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().replace("，", " ").replace("。", " ").split())


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
