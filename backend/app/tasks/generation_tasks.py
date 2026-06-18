import asyncio
import json

from app.models.database import SessionLocal
from app.services.generation_service import GenerationService
from app.services.learning_service import LearningService
from app.services.mindmap_tree_service import MindmapTreeService, tree_to_markdown
from app.services.ws_manager import push_to_user
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.generation_tasks.run_generation_task")
def run_generation_task(task_id: str):
    asyncio.run(_run_generation_task(task_id))


async def _run_generation_task(task_id: str) -> None:
    async with SessionLocal() as db:
        generation = GenerationService(db)
        task = await generation.mark_running(task_id)
        if task is None:
            return
        task = await _update_progress(generation, task, 0, "準備生成")
        payload = json.loads(task.input_json)
        try:
            if task.kind == "quiz":
                output, artifact_id = await _run_quiz(db, generation, task, payload)
            elif task.kind == "flashcards":
                output, artifact_id = await _run_flashcards(db, generation, task, payload)
            elif task.kind == "mindmap":
                output, artifact_id = await _run_mindmap(db, generation, task, payload)
            else:
                raise ValueError(f"Unsupported generation task kind: {task.kind}")
            done_task = await generation.mark_done(task.id, output, artifact_id=artifact_id)
            if done_task:
                await _push_task(done_task, output=output)
        except Exception as exc:
            failed_task = await generation.mark_failed(task.id, str(exc))
            if failed_task:
                await _push_task(failed_task, error=str(exc))


async def _run_quiz(db, generation: GenerationService, task, payload: dict):
    task = await _update_progress(generation, task, 1, "整理教材與題目設定")
    svc = LearningService(db)
    full = ""
    did_stream = False
    async for chunk in svc.stream_quiz(
        task.user_id,
        payload["doc_ids"],
        payload.get("types", ["MC"]),
        int(payload.get("count", 10)),
        payload.get("difficulty", "medium"),
        course_id=payload.get("course_id") if payload.get("publish_to_course") else None,
    ):
        if not did_stream:
            did_stream = True
            task = await _update_progress(generation, task, 2, "AI 正在生成測驗")
        full += chunk
    task = await _update_progress(generation, task, 3, "解析並儲存測驗")
    quiz = await svc.save_quiz(
        task.user_id,
        payload["doc_ids"],
        {
            "types": payload.get("types", ["MC"]),
            "count": payload.get("count", 10),
            "difficulty": payload.get("difficulty", "medium"),
            "course_id": payload.get("course_id"),
            "published": bool(payload.get("publish_to_course")),
        },
        full,
        title=payload.get("title"),
        course_id=payload.get("course_id"),
        publish_to_course=bool(payload.get("publish_to_course")),
        due_at=payload.get("due_at"),
        available_from=payload.get("available_from"),
        answer_visible_at=payload.get("answer_visible_at"),
        attempt_limit=payload.get("attempt_limit"),
    )
    return {"quiz_id": quiz.id, "question_count": payload.get("count", 10)}, quiz.id


async def _run_flashcards(db, generation: GenerationService, task, payload: dict):
    task = await _update_progress(generation, task, 1, "整理教材與閃卡設定")
    svc = LearningService(db)
    doc_ids = payload.get("doc_ids") or ([payload["doc_id"]] if payload.get("doc_id") else [])
    full = ""
    did_stream = False
    async for chunk in svc.stream_flashcards(
        task.user_id,
        doc_ids,
        int(payload.get("count", 10)),
        course_id=payload.get("course_id"),
    ):
        if not did_stream:
            did_stream = True
            task = await _update_progress(generation, task, 2, "AI 正在生成閃卡")
        full += chunk
    task = await _update_progress(generation, task, 3, "解析並儲存閃卡")
    cards = await svc.save_flashcards(task.user_id, doc_ids, full)
    return {"count": len(cards)}, None


async def _run_mindmap(db, generation: GenerationService, task, payload: dict):
    task = await _update_progress(generation, task, 1, "整理教材與心智圖設定")
    doc_id = payload["doc_id"]
    fmt = payload.get("format", "tree_json")
    if fmt == "markdown":
        svc = LearningService(db)
        full = ""
        did_stream = False
        async for chunk in svc.stream_mindmap(task.user_id, doc_id):
            if not did_stream:
                did_stream = True
                task = await _update_progress(generation, task, 2, "AI 正在生成心智圖")
            full += chunk
        task = await _update_progress(generation, task, 3, "儲存心智圖")
        artifact = await svc.save_artifact(task.user_id, doc_id, "mindmap", full)
        return {"mindmap_id": artifact.id, "format": "markdown", "content": full}, artifact.id

    svc = MindmapTreeService(db)
    full = ""
    did_stream = False
    async for chunk in svc.stream_tree(task.user_id, doc_id):
        if not did_stream:
            did_stream = True
            task = await _update_progress(generation, task, 2, "AI 正在生成節點")
        full += chunk
    task = await _update_progress(generation, task, 3, "解析並儲存心智圖")
    artifact = await svc.save_tree(task.user_id, doc_id, full)
    tree = json.loads(artifact.content)
    return {
        "mindmap_id": artifact.id,
        "format": "tree_json",
        "schema_version": tree.get("schema_version"),
        "tree": tree,
        "content": tree_to_markdown(tree),
    }, artifact.id


async def _update_progress(
    generation: GenerationService,
    task,
    current: int,
    message: str,
):
    updated = await generation.update_progress(
        task.id,
        current=current,
        total=task.progress_total,
        message=message,
    )
    if updated is None:
        return task
    await _push_task(updated)
    return updated


async def _push_task(task, output: dict | None = None, error: str | None = None) -> None:
    await _push(
        task.user_id,
        task.id,
        task.kind,
        task.status,
        progress=GenerationService.progress_payload(task),
        output=output,
        error=error,
    )


async def _push(
    user_id: str,
    task_id: str,
    kind: str,
    status: str,
    progress: dict | None = None,
    output: dict | None = None,
    error: str | None = None,
) -> None:
    await push_to_user(
        user_id,
        {
            "type": "generation_task",
            "task_id": task_id,
            "kind": kind,
            "status": status,
            "progress": progress,
            "output": output,
            "error": error,
        },
    )
