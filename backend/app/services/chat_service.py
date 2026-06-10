import json
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
    )
    db.add(assistant_msg)
    await db.commit()

    yield "data: [DONE]\n\n"
