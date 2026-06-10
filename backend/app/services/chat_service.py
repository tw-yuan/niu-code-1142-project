import json
import re
from typing import AsyncGenerator
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.learning_session import LearningSession
from app.models.chat_message import ChatMessage
from app.services.rag_service import get_context_with_sources
from app.services.direction_service import get_direction_system_prompt


async def get_chat_history(db: AsyncSession, session_id: int) -> list[dict]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]


def _first_lines(text: str, limit: int = 5) -> list[str]:
    lines = []
    for line in text.splitlines():
        clean = line.strip(" -#\t")
        if len(clean) >= 8:
            lines.append(clean[:120])
        if len(lines) >= limit:
            break
    return lines


def _demo_response(direction_key: str, direction_label: str, user_message: str, context: str) -> str:
    lines = _first_lines(context)
    bullets = "\n".join(f"- {line}" for line in lines) or "- 這份講義已完成解析，可用來摘要、提問與自我測驗。"
    if direction_key == "quiz":
        return (
            "以下是根據講義內容產生的示範測驗：\n\n"
            "1. 請用自己的話說明講義中第一個核心概念。\n"
            "2. 講義提到的流程或步驟可以分成哪幾個階段？\n"
            "3. 請舉一個可套用本講義概念的例子。\n\n"
            "作答後我會依照講義片段協助批改與補強。"
        )
    if direction_key == "summary":
        return f"這是示範模式產生的講義摘要：\n\n{bullets}\n\n你可以接著要求我整理章節架構或考前重點。"
    if direction_key == "explain":
        return f"我會先用講義中的內容建立概念脈絡。這次問題是「{user_message}」。可先掌握：\n\n{bullets}"
    return f"目前以「{direction_label}」方向協助你。根據講義片段，可先從這些重點開始：\n\n{bullets}"


def _quiz_metadata(direction_key: str, user_message: str, assistant_response: str) -> dict | None:
    if direction_key != "quiz":
        return None
    score = None
    match = re.search(r"(\d{1,3})\s*(?:/|／|分|%)", assistant_response)
    if match:
        score = min(100, int(match.group(1)))
    question_count = len(re.findall(r"(^|\n)\s*\d+[.、]", assistant_response))
    return {
        "kind": "quiz",
        "question_count": question_count or None,
        "score": score,
        "status": "graded" if score is not None else "generated",
        "student_input_preview": user_message[:160],
    }


async def _yield_and_store_demo_response(
    db: AsyncSession,
    learning_session: LearningSession,
    user_message: str,
    context: str,
    sources: list[dict],
) -> AsyncGenerator[str, None]:
    full_response = _demo_response(
        learning_session.direction_key,
        learning_session.direction_label,
        user_message,
        context,
    )
    for i in range(0, len(full_response), 18):
        safe = full_response[i:i + 18].replace("\n", "\\n")
        yield f"data: {safe}\n\n"

    assistant_msg = ChatMessage(
        session_id=learning_session.id,
        role="assistant",
        content=full_response,
        context_chunks_used=json.dumps(sources, ensure_ascii=False),
        quiz_metadata=json.dumps(_quiz_metadata(learning_session.direction_key, user_message, full_response), ensure_ascii=False)
        if learning_session.direction_key == "quiz" else None,
    )
    db.add(assistant_msg)
    await db.commit()
    yield "data: [DONE]\n\n"


async def stream_chat_response(
    db: AsyncSession,
    learning_session: LearningSession,
    user_message: str,
) -> AsyncGenerator[str, None]:
    from app.models.document import Document

    doc_result = await db.execute(
        select(Document).where(Document.id == learning_session.document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc or not doc.parsed_text:
        yield "data: [ERROR] 找不到文件內容\n\n"
        return

    context, sources = await get_context_with_sources(
        doc_id=doc.id,
        user_id=doc.user_id,
        token_count=doc.token_count,
        full_text=doc.parsed_text,
        query=user_message,
    )

    system_prompt = get_direction_system_prompt(
        learning_session.direction_key,
        learning_session.direction_label if learning_session.direction_key not in ("qa", "summary", "explain", "quiz") else None,
    )
    system_prompt += (
        "\n\n回答時請優先引用講義內容；如果答案超出講義範圍，請明確標示。"
        "\n\n以下是講義內容：\n\n"
        f"{context}"
    )

    history = await get_chat_history(db, learning_session.id)

    user_msg = ChatMessage(
        session_id=learning_session.id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    await db.commit()

    if settings.demo_mode or not settings.openai_compatible_api_key:
        async for item in _yield_and_store_demo_response(db, learning_session, user_message, context, sources):
            yield item
        return

    oai = AsyncOpenAI(
        base_url=settings.openai_compatible_base_url,
        api_key=settings.openai_compatible_api_key or "none",
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    full_response = ""
    try:
        stream = await oai.chat.completions.create(
            model=settings.openai_compatible_model,
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=2000,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_response += delta
                safe = delta.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"
        return

    assistant_msg = ChatMessage(
        session_id=learning_session.id,
        role="assistant",
        content=full_response,
        context_chunks_used=json.dumps(sources, ensure_ascii=False),
        quiz_metadata=json.dumps(_quiz_metadata(learning_session.direction_key, user_message, full_response), ensure_ascii=False)
        if learning_session.direction_key == "quiz" else None,
    )
    db.add(assistant_msg)
    await db.commit()

    yield "data: [DONE]\n\n"
