import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import (
    Document,
    Flashcard,
    LearningArtifact,
    Quiz,
    QuizAttempt,
)
from app.schemas import (
    FlashcardCreate,
    FlashcardUpdate,
    QuizAttemptRequest,
)
from app.services.chroma_service import ChromaService
from app.services.json_utils import parse_json_llm, to_json
from app.services.llm_client import LLMClient
from app.services.prompt_loader import load_prompt


class LearningService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def stream_summary(self, user_id: str, doc_id: str, kind: str, count: int):
        doc = await self._get_document(user_id, doc_id)
        context = await self._context(user_id, [doc_id])
        prompt_name = "summary_bullets" if kind == "bullets" else "summary_full"
        if prompt_name == "summary_bullets":
            system, cfg = load_prompt(prompt_name, document_title=doc.filename, count=count)
        else:
            system, cfg = load_prompt(prompt_name, document_title=doc.filename)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"參考資料：\n{context}"},
        ]
        async for chunk in LLMClient(self.db).stream_chat(
            messages,
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
            feature="summary",
            user_id=user_id,
        ):
            yield chunk

    async def save_artifact(self, user_id: str, doc_id: str, kind: str, content: str) -> LearningArtifact:
        await self._get_document(user_id, doc_id)
        artifact = LearningArtifact(user_id=user_id, doc_id=doc_id, kind=kind, content=content)
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact

    async def latest_artifact(self, user_id: str, doc_id: str, kind: str) -> LearningArtifact:
        artifact = (
            await self.db.execute(
                select(LearningArtifact)
                .where(
                    and_(
                        LearningArtifact.user_id == user_id,
                        LearningArtifact.doc_id == doc_id,
                        LearningArtifact.kind == kind,
                    )
                )
                .order_by(desc(LearningArtifact.created_at))
            )
        ).scalar_one_or_none()
        if artifact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
        return artifact

    async def stream_mindmap(self, user_id: str, doc_id: str):
        doc = await self._get_document(user_id, doc_id)
        context = await self._context(user_id, [doc_id])
        system, cfg = load_prompt("mindmap", document_title=doc.filename)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"參考資料：\n{context}"},
        ]
        async for chunk in LLMClient(self.db).stream_chat(
            messages,
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
            feature="mindmap",
            user_id=user_id,
        ):
            yield chunk

    async def stream_quiz(
        self,
        user_id: str,
        doc_ids: list[str],
        types: list[str],
        count: int,
        difficulty: str,
    ):
        await self._validate_documents(user_id, doc_ids)
        context = await self._context(user_id, doc_ids)
        system, cfg = load_prompt(
            "quiz_generate",
            types=", ".join(types),
            count=count,
            difficulty=difficulty,
            context=context,
        )
        messages = [{"role": "system", "content": system}]
        async for chunk in LLMClient(self.db).stream_chat(
            messages,
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
            response_format={"type": "json_object"},
            feature="quiz",
            user_id=user_id,
        ):
            yield chunk

    async def save_quiz(
        self,
        user_id: str,
        doc_ids: list[str],
        config: dict[str, Any],
        json_text: str,
    ) -> Quiz:
        parsed = parse_json_llm(json_text)
        questions = parsed.get("questions", [])
        if not isinstance(questions, list):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid quiz JSON")
        quiz = Quiz(
            user_id=user_id,
            title="AI 生成測驗",
            doc_ids=to_json(doc_ids),
            config=to_json(config),
            questions=to_json(questions),
        )
        self.db.add(quiz)
        await self.db.commit()
        await self.db.refresh(quiz)
        return quiz

    async def list_quizzes(self, user_id: str) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(Quiz).where(Quiz.user_id == user_id).order_by(desc(Quiz.created_at))
            )
        ).scalars().all()
        return [self._quiz_out(row) for row in rows]

    async def get_quiz(self, user_id: str, quiz_id: str) -> dict[str, Any]:
        quiz = await self._get_quiz(user_id, quiz_id)
        return self._quiz_out(quiz)

    async def submit_quiz_attempt(
        self, user_id: str, quiz_id: str, body: QuizAttemptRequest
    ) -> dict[str, Any]:
        quiz = await self._get_quiz(user_id, quiz_id)
        questions = json.loads(quiz.questions)
        score = _score_quiz(questions, body.answers)
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            user_id=user_id,
            answers=to_json(body.answers),
            total_score=score,
            duration_sec=body.duration_sec,
        )
        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        return {
            "id": attempt.id,
            "quiz_id": quiz.id,
            "total_score": attempt.total_score,
            "completed_at": attempt.completed_at,
        }

    async def quiz_attempts(self, user_id: str, quiz_id: str) -> list[dict[str, Any]]:
        await self._get_quiz(user_id, quiz_id)
        attempts = (
            await self.db.execute(
                select(QuizAttempt)
                .where(and_(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id))
                .order_by(desc(QuizAttempt.completed_at))
            )
        ).scalars().all()
        return [
            {
                "id": attempt.id,
                "quiz_id": attempt.quiz_id,
                "answers": json.loads(attempt.answers),
                "total_score": attempt.total_score,
                "duration_sec": attempt.duration_sec,
                "completed_at": attempt.completed_at,
            }
            for attempt in attempts
        ]

    async def wrongbook(self, user_id: str) -> list[dict[str, Any]]:
        quizzes = (
            await self.db.execute(select(Quiz).where(Quiz.user_id == user_id))
        ).scalars().all()
        result: list[dict[str, Any]] = []
        for quiz in quizzes:
            questions = json.loads(quiz.questions)
            for idx, question in enumerate(questions):
                result.append(
                    {
                        "quiz_id": quiz.id,
                        "question_index": idx,
                        "question": question.get("question"),
                        "answer": question.get("answer"),
                        "explanation": question.get("explanation"),
                    }
                )
        return result[:50]

    async def stream_flashcards(self, user_id: str, doc_id: str, count: int):
        doc = await self._get_document(user_id, doc_id)
        context = await self._context(user_id, [doc_id])
        system, cfg = load_prompt("flashcard_generate", document_title=doc.filename, count=count)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"參考資料：\n{context}"},
        ]
        async for chunk in LLMClient(self.db).stream_chat(
            messages,
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
            response_format={"type": "json_object"},
            feature="flashcards",
            user_id=user_id,
        ):
            yield chunk

    async def save_flashcards(self, user_id: str, doc_id: str, json_text: str) -> list[Flashcard]:
        parsed = parse_json_llm(json_text)
        cards = parsed.get("cards", [])
        if not isinstance(cards, list):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid flashcard JSON")
        result: list[Flashcard] = []
        for card in cards:
            flashcard = Flashcard(
                user_id=user_id,
                doc_id=doc_id,
                front=str(card.get("front", "")),
                back=str(card.get("back", "")),
                source_page=card.get("source_page"),
            )
            if flashcard.front and flashcard.back:
                self.db.add(flashcard)
                result.append(flashcard)
        await self.db.commit()
        return result

    async def list_flashcards(self, user_id: str) -> list[dict[str, Any]]:
        cards = (
            await self.db.execute(
                select(Flashcard).where(Flashcard.user_id == user_id).order_by(Flashcard.next_review)
            )
        ).scalars().all()
        return [self._flashcard_out(card) for card in cards]

    async def create_flashcard(self, user_id: str, body: FlashcardCreate) -> dict[str, Any]:
        if body.doc_id:
            await self._get_document(user_id, body.doc_id)
        card = Flashcard(
            user_id=user_id,
            doc_id=body.doc_id,
            front=body.front,
            back=body.back,
            source_page=body.source_page,
        )
        self.db.add(card)
        await self.db.commit()
        await self.db.refresh(card)
        return self._flashcard_out(card)

    async def update_flashcard(
        self, user_id: str, card_id: str, body: FlashcardUpdate
    ) -> dict[str, Any]:
        card = await self._get_flashcard(user_id, card_id)
        if body.front is not None:
            card.front = body.front
        if body.back is not None:
            card.back = body.back
        if body.source_page is not None:
            card.source_page = body.source_page
        await self.db.commit()
        return self._flashcard_out(card)

    async def delete_flashcard(self, user_id: str, card_id: str) -> None:
        card = await self._get_flashcard(user_id, card_id)
        await self.db.delete(card)
        await self.db.commit()

    async def review_flashcard(self, user_id: str, card_id: str, quality: int) -> dict[str, Any]:
        card = await self._get_flashcard(user_id, card_id)
        if quality < 3:
            card.repetition = 0
            card.interval_days = 1
        else:
            if card.repetition == 0:
                card.interval_days = 1
            elif card.repetition == 1:
                card.interval_days = 6
            else:
                card.interval_days = max(1, round(card.interval_days * card.ease_factor))
            card.repetition += 1
        card.ease_factor = max(
            1.3, card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        )
        card.next_review = (
            datetime.now(UTC) + timedelta(days=card.interval_days)
        ).isoformat()
        await self.db.commit()
        return self._flashcard_out(card)

    async def _context(self, user_id: str, doc_ids: list[str]) -> str:
        chunks = await ChromaService().get_document_chunks(user_id, doc_ids)
        text = "\n\n".join(
            f"[{idx}] {item['metadata'].get('filename')} 第 {item['metadata'].get('page_num')} 頁\n{item['text']}"
            for idx, item in enumerate(chunks, 1)
        )
        return text[:14000] or "目前沒有可用的參考資料。"

    async def _validate_documents(self, user_id: str, doc_ids: list[str]) -> list[Document]:
        docs = (
            await self.db.execute(
                select(Document).where(and_(Document.user_id == user_id, Document.id.in_(doc_ids)))
            )
        ).scalars().all()
        if set(doc.id for doc in docs) != set(doc_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return list(docs)

    async def _get_document(self, user_id: str, doc_id: str) -> Document:
        doc = (
            await self.db.execute(
                select(Document).where(and_(Document.user_id == user_id, Document.id == doc_id))
            )
        ).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return doc

    async def _get_quiz(self, user_id: str, quiz_id: str) -> Quiz:
        quiz = (
            await self.db.execute(select(Quiz).where(and_(Quiz.user_id == user_id, Quiz.id == quiz_id)))
        ).scalar_one_or_none()
        if quiz is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
        return quiz

    async def _get_flashcard(self, user_id: str, card_id: str) -> Flashcard:
        card = (
            await self.db.execute(
                select(Flashcard).where(and_(Flashcard.user_id == user_id, Flashcard.id == card_id))
            )
        ).scalar_one_or_none()
        if card is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")
        return card

    def _quiz_out(self, quiz: Quiz) -> dict[str, Any]:
        return {
            "id": quiz.id,
            "title": quiz.title,
            "doc_ids": json.loads(quiz.doc_ids),
            "config": json.loads(quiz.config),
            "questions": json.loads(quiz.questions),
            "created_at": quiz.created_at,
        }

    def _flashcard_out(self, card: Flashcard) -> dict[str, Any]:
        return {
            "id": card.id,
            "doc_id": card.doc_id,
            "front": card.front,
            "back": card.back,
            "source_page": card.source_page,
            "repetition": card.repetition,
            "ease_factor": card.ease_factor,
            "interval_days": card.interval_days,
            "next_review": card.next_review,
            "created_at": card.created_at,
        }


def _score_quiz(questions: list[dict[str, Any]], answers: dict[str, Any] | list[Any]) -> float:
    if not questions:
        return 0.0
    correct = 0
    for idx, question in enumerate(questions):
        expected = question.get("answer")
        actual = answers.get(str(idx)) if isinstance(answers, dict) else answers[idx] if idx < len(answers) else None
        if actual == expected:
            correct += 1
    return correct / len(questions)
