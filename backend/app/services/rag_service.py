import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import ChatMessage, ChatSession, Document, now_iso
from app.schemas import ChatSessionCreate
from app.services.chroma_service import ChromaService
from app.services.courses_service import CoursesService
from app.services.json_utils import from_json_list, to_json
from app.services.llm_client import LLMClient
from app.services.prompt_loader import load_prompt


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._last_citations: list[dict[str, Any]] = []

    async def create_session(self, user_id: str, body: ChatSessionCreate) -> dict[str, Any]:
        shared_doc_ids = []
        if body.course_id:
            shared_doc_ids = await CoursesService(self.db).course_document_ids(user_id, body.course_id)
            if not set(body.doc_ids).issubset(set(shared_doc_ids)):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
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
        if prompt_name == "rag_socratic":
            system_prompt, cfg = load_prompt(prompt_name, context=context, question=question)
        else:
            system_prompt, cfg = load_prompt(prompt_name, context=context)

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
                select(Document.id).where(and_(Document.user_id == user_id, Document.id.in_(doc_ids)))
            )
        ).scalars().all()
        allowed = set(rows) | set(shared_doc_ids or [])
        if not set(doc_ids).issubset(allowed):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

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
                }
            )
        return "\n\n".join(parts), citations

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
