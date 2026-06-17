import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, rate_limit
from app.models.tables import User
from app.schemas import MindmapExpandRequest, MindmapRequest
from app.services.cost_service import check_quota
from app.services.document_service import DocumentService
from app.services.generation_service import GenerationService
from app.services.learning_service import LearningService
from app.services.mindmap_tree_service import MindmapTreeService, tree_to_markdown
from app.tasks.generation_tasks import run_generation_task

router = APIRouter(prefix="/mindmap", tags=["mindmap"])


@router.post("/jobs", dependencies=[rate_limit("mindmap_job", 5, 3600)])
async def create_mindmap_job(
    body: MindmapRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await DocumentService(db).get_document(current_user.id, body.doc_id)
    await check_quota(db, current_user.id)
    task = await GenerationService(db).create_task(
        current_user.id,
        "mindmap",
        body.model_dump(),
    )
    run_generation_task.delay(task["id"])
    return task


@router.post("/stream", dependencies=[rate_limit("mindmap_stream", 5, 3600)])
async def stream_mindmap(
    body: MindmapRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await DocumentService(db).get_document(current_user.id, body.doc_id)
    await check_quota(db, current_user.id)
    legacy_svc = LearningService(db)
    tree_svc = MindmapTreeService(db)

    async def event_stream():
        full = ""
        try:
            if body.format == "markdown":
                async for chunk in legacy_svc.stream_mindmap(current_user.id, body.doc_id):
                    full += chunk
                    yield _sse({"type": "chunk", "content": chunk})
                artifact = await legacy_svc.save_artifact(
                    current_user.id, body.doc_id, "mindmap", full
                )
                yield _sse(
                    {
                        "type": "mindmap_meta",
                        "data": {"mindmap_id": artifact.id, "format": "markdown"},
                    }
                )
            else:
                async for chunk in tree_svc.stream_tree(current_user.id, body.doc_id):
                    full += chunk
                    yield _sse({"type": "chunk", "content": chunk})
                artifact = await tree_svc.save_tree(current_user.id, body.doc_id, full)
                tree = json.loads(artifact.content)
                yield _sse({"type": "mindmap_tree", "data": tree})
                yield _sse(
                    {
                        "type": "mindmap_meta",
                        "data": {
                            "mindmap_id": artifact.id,
                            "format": "tree_json",
                            "schema_version": tree.get("schema_version"),
                        },
                    }
                )
        except Exception as exc:
            yield _sse({"type": "error", "code": "mindmap_error", "message": str(exc)})
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{doc_id}")
async def get_mindmap(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MindmapTreeService(db).latest_mindmap(current_user.id, doc_id)


@router.post(
    "/{artifact_id}/nodes/{node_id}/expand/stream",
    dependencies=[rate_limit("mindmap_expand", 15, 3600)],
)
async def expand_mindmap_node(
    artifact_id: str,
    node_id: str,
    body: MindmapExpandRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_quota(db, current_user.id)
    svc = MindmapTreeService(db)

    async def event_stream():
        full = ""
        try:
            async for chunk in svc.stream_expand_node(
                current_user.id,
                artifact_id,
                node_id,
                max_children=body.max_children,
            ):
                full += chunk
                yield _sse({"type": "chunk", "content": chunk})
            artifact, tree, children = await svc.save_expanded_node(
                current_user.id, artifact_id, node_id, full
            )
            yield _sse(
                {
                    "type": "mindmap_patch",
                    "data": {
                        "op": "append_children",
                        "mindmap_id": artifact.id,
                        "node_id": node_id,
                        "children": children,
                        "tree": tree,
                        "content": tree_to_markdown(tree),
                    },
                }
            )
        except Exception as exc:
            yield _sse({"type": "error", "code": "mindmap_expand_error", "message": str(exc)})
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.put("/{artifact_id}")
async def update_mindmap(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    _ = db
    return {"id": artifact_id, "detail": "Mindmap editing API is reserved for the next phase"}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
