import json
import re
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Document, LearningArtifact, now_iso
from app.services.chroma_service import ChromaService
from app.services.document_access import DocumentAccessService
from app.services.json_utils import parse_json_llm, to_json
from app.services.llm_client import LLMClient
from app.services.prompt_loader import load_prompt

MINDMAP_TREE_KIND = "mindmap_tree"
MINDMAP_MARKDOWN_KIND = "mindmap"
MINDMAP_SCHEMA_VERSION = 2
MAX_INITIAL_DEPTH = 4
MAX_EXPAND_DEPTH = 5
MAX_CHILDREN = 6
MAX_NODES = 80
MAX_LABEL_LEN = 36

MindmapTree = dict[str, Any]


class MindmapTreeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def stream_tree(self, user_id: str, doc_id: str) -> AsyncGenerator[str, None]:
        doc = await self._get_document(user_id, doc_id)
        context = await self._context(user_id, [doc_id])
        system, cfg = load_prompt("mindmap_tree", document_title=doc.filename)
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    "請依照 system 指示，只回傳心智圖 JSON object。\n\n"
                    "<reference_material>\n"
                    f"{context}\n"
                    "</reference_material>"
                ),
            },
        ]
        async for chunk in LLMClient(self.db).stream_chat(
            messages,
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
            response_format={"type": "json_object"},
            feature="mindmap",
            user_id=user_id,
        ):
            yield chunk

    async def save_tree(self, user_id: str, doc_id: str, json_text: str) -> LearningArtifact:
        doc = await self._get_document(user_id, doc_id)
        parsed = _parse_mindmap_json(json_text, fallback_title=doc.filename)
        tree = normalize_mindmap_tree(parsed, doc_id=doc.id, fallback_title=doc.filename)
        artifact = LearningArtifact(
            user_id=user_id,
            doc_id=doc.id,
            kind=MINDMAP_TREE_KIND,
            content=to_json(tree),
        )
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact

    async def latest_mindmap(self, user_id: str, doc_id: str) -> dict[str, Any]:
        await self._get_document(user_id, doc_id)
        tree_artifact = await self._latest_artifact(user_id, doc_id, MINDMAP_TREE_KIND)
        if tree_artifact:
            tree = _safe_tree(tree_artifact.content)
            if tree:
                content = tree_to_markdown(tree)
                return {
                    "id": tree_artifact.id,
                    "doc_id": tree_artifact.doc_id,
                    "format": "tree_json",
                    "schema_version": MINDMAP_SCHEMA_VERSION,
                    "tree": tree,
                    "content": content,
                }
        markdown_artifact = await self._latest_artifact(user_id, doc_id, MINDMAP_MARKDOWN_KIND)
        if markdown_artifact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
        return {
            "id": markdown_artifact.id,
            "doc_id": markdown_artifact.doc_id,
            "format": "markdown",
            "schema_version": 1,
            "tree": markdown_to_tree(markdown_artifact.content, doc_id=doc_id),
            "content": markdown_artifact.content,
        }

    async def list_document_status(self, user_id: str) -> list[dict[str, Any]]:
        documents = [
            doc
            for doc in await DocumentAccessService(self.db).list_accessible_documents(user_id)
            if doc.status != "archived"
        ]
        doc_ids = [doc.id for doc in documents]
        artifacts_by_doc: dict[str, LearningArtifact] = {}
        if doc_ids:
            artifacts = (
                await self.db.execute(
                    select(LearningArtifact)
                    .where(
                        and_(
                            LearningArtifact.user_id == user_id,
                            LearningArtifact.doc_id.in_(doc_ids),
                            LearningArtifact.kind.in_(
                                [MINDMAP_TREE_KIND, MINDMAP_MARKDOWN_KIND]
                            ),
                        )
                    )
                    .order_by(desc(LearningArtifact.created_at))
                )
            ).scalars().all()
            for artifact in artifacts:
                if artifact.doc_id not in artifacts_by_doc:
                    artifacts_by_doc[artifact.doc_id] = artifact

        rows = []
        for doc in documents:
            artifact = artifacts_by_doc.get(doc.id)
            rows.append(
                {
                    "document": {
                        "id": doc.id,
                        "user_id": doc.user_id,
                        "filename": doc.filename,
                        "file_type": doc.file_type,
                        "file_size": doc.file_size,
                        "status": doc.status,
                        "page_count": doc.page_count,
                        "chunk_count": doc.chunk_count,
                        "error_msg": doc.error_msg,
                        "created_at": doc.created_at,
                        "updated_at": doc.updated_at,
                    },
                    "has_mindmap": artifact is not None,
                    "mindmap_id": artifact.id if artifact else None,
                    "format": _artifact_format(artifact) if artifact else None,
                    "updated_at": artifact.updated_at if artifact else None,
                }
            )
        return rows

    async def stream_expand_node(
        self,
        user_id: str,
        artifact_id: str,
        node_id: str,
        max_children: int = 5,
    ) -> AsyncGenerator[str, None]:
        artifact = await self._get_tree_artifact(user_id, artifact_id)
        tree = _safe_tree(artifact.content)
        if not tree:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid mindmap tree")
        node_path = find_node_path(tree, node_id)
        if not node_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mindmap node not found")
        target = node_path[-1]
        target_depth = int(target.get("depth") or len(node_path) - 1)
        if target_depth >= MAX_EXPAND_DEPTH:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum mindmap depth reached")

        async for chunk in self._stream_children_json(
            user_id=user_id,
            doc_id=str(tree.get("doc_id") or artifact.doc_id),
            node_path=[str(node.get("title") or "") for node in node_path],
            max_children=max(1, min(max_children, MAX_CHILDREN)),
        ):
            yield chunk

    async def save_expanded_node(
        self,
        user_id: str,
        artifact_id: str,
        node_id: str,
        json_text: str,
    ) -> tuple[LearningArtifact, MindmapTree, list[dict[str, Any]]]:
        artifact = await self._get_tree_artifact(user_id, artifact_id)
        tree = _safe_tree(artifact.content)
        if not tree:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid mindmap tree")
        node_path = find_node_path(tree, node_id)
        if not node_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mindmap node not found")
        target = node_path[-1]
        target_depth = int(target.get("depth") or len(node_path) - 1)
        parsed = _parse_mindmap_children_json(json_text)
        children = parsed.get("children", [])
        if not isinstance(children, list):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid mindmap expansion JSON")
        normalized_children = _normalize_children(
            children,
            doc_id=str(tree.get("doc_id") or artifact.doc_id),
            parent_id=node_id,
            depth=target_depth + 1,
            max_depth=MAX_EXPAND_DEPTH,
            node_budget=max(0, MAX_NODES - count_nodes(tree)),
            id_prefix=f"{node_id}-x",
        )
        existing_titles = {str(child.get("title") or "").strip() for child in target.get("children", [])}
        appended = [child for child in normalized_children if child["title"] not in existing_titles]
        target.setdefault("children", []).extend(appended)
        target["children_loaded"] = True
        target["expandable"] = bool(target.get("children"))
        tree["updated_at"] = now_iso()
        artifact.content = to_json(tree)
        artifact.updated_at = now_iso()
        await self.db.commit()
        return artifact, tree, appended

    async def _stream_children_json(
        self,
        user_id: str,
        doc_id: str,
        node_path: list[str],
        max_children: int,
    ) -> AsyncGenerator[str, None]:
        doc = await self._get_document(user_id, doc_id)
        context = await self._focused_context(user_id, doc_id, " > ".join(node_path))
        system, cfg = load_prompt(
            "mindmap_expand",
            document_title=doc.filename,
            node_path=" > ".join(node_path),
            max_children=max_children,
        )
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    "請依照 system 指示，只回傳節點展開 JSON object。\n\n"
                    "<reference_material>\n"
                    f"{context}\n"
                    "</reference_material>"
                ),
            },
        ]
        async for chunk in LLMClient(self.db).stream_chat(
            messages,
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
            response_format={"type": "json_object"},
            feature="mindmap_expand",
            user_id=user_id,
        ):
            yield chunk

    async def _focused_context(self, user_id: str, doc_id: str, query: str) -> str:
        shared_doc_ids = await DocumentAccessService(self.db).shared_doc_ids(user_id, [doc_id])
        llm = LLMClient(self.db)
        embedding = (await llm.embed([query], user_id=user_id))[0]
        chunks = await ChromaService().query_chunks(
            user_id,
            embedding,
            doc_ids=[doc_id],
            shared_doc_ids=shared_doc_ids,
            n_results=8,
        )
        if not chunks:
            return await self._context(user_id, [doc_id])
        return "\n\n".join(
            f"[{idx}] {item['metadata'].get('filename')} 第 {item['metadata'].get('page_num')} 頁\n{item['text']}"
            for idx, item in enumerate(chunks, 1)
        )[:12000]

    async def _context(self, user_id: str, doc_ids: list[str]) -> str:
        shared_doc_ids = await DocumentAccessService(self.db).shared_doc_ids(user_id, doc_ids)
        chunks = await ChromaService().get_document_chunks(user_id, doc_ids, shared_doc_ids)
        text = "\n\n".join(
            f"[{idx}] {item['metadata'].get('filename')} 第 {item['metadata'].get('page_num')} 頁\n{item['text']}"
            for idx, item in enumerate(chunks, 1)
        )
        return text[:14000] or "目前沒有可用的參考資料。"

    async def _latest_artifact(self, user_id: str, doc_id: str, kind: str) -> LearningArtifact | None:
        return (
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
        ).scalars().first()

    async def _get_tree_artifact(self, user_id: str, artifact_id: str) -> LearningArtifact:
        artifact = (
            await self.db.execute(
                select(LearningArtifact).where(
                    and_(
                        LearningArtifact.id == artifact_id,
                        LearningArtifact.user_id == user_id,
                        LearningArtifact.kind == MINDMAP_TREE_KIND,
                    )
                )
            )
        ).scalar_one_or_none()
        if artifact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mindmap not found")
        return artifact

    async def _get_document(self, user_id: str, doc_id: str) -> Document:
        doc = (
            await self.db.execute(
                select(Document).where(
                    and_(
                        Document.id == doc_id,
                        DocumentAccessService(self.db).accessible_document_condition(user_id),
                    )
                )
            )
        ).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return doc


def normalize_mindmap_tree(parsed: dict[str, Any], doc_id: str, fallback_title: str) -> MindmapTree:
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid mindmap JSON")
    title = _clean_label(parsed.get("title") or fallback_title, fallback_title, max_len=64)
    raw_root = parsed.get("root")
    if isinstance(raw_root, dict):
        root_title = raw_root.get("title") or raw_root.get("label") or title
        raw_children = raw_root.get("children", [])
        raw_summary = raw_root.get("summary")
    else:
        root_title = title
        raw_children = parsed.get("nodes") or parsed.get("children") or []
        raw_summary = parsed.get("summary")
    children = _normalize_children(
        raw_children if isinstance(raw_children, list) else [],
        doc_id=doc_id,
        parent_id="root",
        depth=1,
        max_depth=MAX_INITIAL_DEPTH,
        node_budget=MAX_NODES - 1,
        id_prefix="n",
    )
    return {
        "schema_version": MINDMAP_SCHEMA_VERSION,
        "title": title,
        "doc_id": doc_id,
        "root": {
            "id": "root",
            "title": _clean_label(root_title, title, max_len=64),
            "summary": _clean_summary(raw_summary),
            "depth": 0,
            "order": 0,
            "expandable": bool(children),
            "children_loaded": True,
            "children": children,
            "source_refs": _source_refs(raw_root if isinstance(raw_root, dict) else parsed),
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def _artifact_format(artifact: LearningArtifact | None) -> str | None:
    if artifact is None:
        return None
    if artifact.kind == MINDMAP_TREE_KIND:
        return "tree_json"
    if artifact.kind == MINDMAP_MARKDOWN_KIND:
        return "markdown"
    return artifact.kind


def _parse_mindmap_json(text: str, fallback_title: str) -> dict[str, Any]:
    try:
        return parse_json_llm(text)
    except json.JSONDecodeError:
        repaired = _repair_json_text(text)
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
    fallback_children = _fallback_children_from_text(text)
    return {
        "title": fallback_title,
        "summary": "AI 輸出 JSON 格式不完整，已保留可辨識的節點內容。",
        "root": {
            "title": fallback_title,
            "summary": "AI 輸出 JSON 格式不完整，已用可解析內容建立心智圖。",
            "children": fallback_children,
        },
    }


def _parse_mindmap_children_json(text: str) -> dict[str, Any]:
    try:
        return parse_json_llm(text)
    except json.JSONDecodeError:
        repaired = _repair_json_text(text)
        if repaired:
            try:
                parsed = json.loads(repaired)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return {"children": _fallback_children_from_text(text)}


def _repair_json_text(text: str) -> str | None:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    if not cleaned:
        return None
    start = cleaned.find("{")
    if start > 0:
        cleaned = cleaned[start:]
    end = cleaned.rfind("}")
    if end >= 0:
        cleaned = cleaned[: end + 1]
    cleaned = _escape_control_chars_in_strings(cleaned)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return _close_json_fragment(cleaned)


def _escape_control_chars_in_strings(text: str) -> str:
    result: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\":
            result.append(char)
            escaped = True
            continue
        if char == '"':
            result.append(char)
            in_string = not in_string
            continue
        if in_string and char in {"\n", "\r", "\t"}:
            result.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[char])
        else:
            result.append(char)
    return "".join(result)


def _close_json_fragment(text: str) -> str:
    stack: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            stack.append("}")
        elif char == "[":
            stack.append("]")
        elif char in {"}", "]"} and stack and stack[-1] == char:
            stack.pop()
    suffix = '"' if in_string else ""
    suffix += "".join(reversed(stack))
    return f"{text}{suffix}"


def _fallback_children_from_text(text: str) -> list[dict[str, Any]]:
    labels: list[str] = []
    patterns = [
        r'"title"\s*:\s*"([^"]+)"',
        r'"label"\s*:\s*"([^"]+)"',
        r"^\s*[-*+]\s+(.+)$",
        r"^\s*#{1,6}\s+(.+)$",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            label = _clean_label(match.group(1), "", max_len=MAX_LABEL_LEN)
            if label and label not in labels:
                labels.append(label)
            if len(labels) >= 12:
                break
        if labels:
            break
    return [
        {
            "title": label,
            "summary": None,
            "type": "concept",
            "source_refs": [],
            "children": [],
        }
        for label in labels[:MAX_CHILDREN]
    ]


def markdown_to_tree(markdown: str, doc_id: str) -> MindmapTree:
    root: dict[str, Any] = {
        "id": "root",
        "title": "心智圖",
        "summary": None,
        "depth": 0,
        "order": 0,
        "expandable": False,
        "children_loaded": True,
        "children": [],
        "source_refs": [],
    }
    stack: list[tuple[int, dict[str, Any]]] = [(0, root)]
    counter = 0
    bullet_base_depth = 2
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("```"):
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            depth = len(heading.group(1))
            label = _clean_label(heading.group(2), "", max_len=MAX_LABEL_LEN)
            bullet_base_depth = depth + 1
        else:
            bullet = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.+)$", raw.rstrip())
            if not bullet:
                continue
            depth = bullet_base_depth + len(bullet.group(1)) // 2
            label = _clean_label(bullet.group(3), "", max_len=MAX_LABEL_LEN)
        if depth == 1 and not root["children"] and root["title"] == "心智圖":
            root["title"] = label
            continue
        while len(stack) > 1 and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1][1]
        node = _node(
            node_id=f"legacy-{counter}",
            title=label,
            depth=len(stack),
            order=len(parent["children"]),
            children=[],
            doc_id=doc_id,
            raw={},
        )
        counter += 1
        parent["children"].append(node)
        parent["expandable"] = True
        stack.append((depth, node))
    return {
        "schema_version": 1,
        "title": root["title"],
        "doc_id": doc_id,
        "root": root,
    }


def tree_to_markdown(tree: MindmapTree) -> str:
    root = tree.get("root") if isinstance(tree.get("root"), dict) else {}
    lines = [f"# {root.get('title') or tree.get('title') or '心智圖'}"]

    def walk(nodes: list[dict[str, Any]], depth: int) -> None:
        for node in nodes:
            title = str(node.get("title") or "").strip()
            if not title:
                continue
            if depth == 1:
                lines.append(f"## {title}")
            else:
                lines.append(f"{'  ' * (depth - 2)}- {title}")
            children = node.get("children")
            if isinstance(children, list):
                walk(children, depth + 1)

    children = root.get("children")
    if isinstance(children, list):
        walk(children, 1)
    return "\n".join(lines)


def find_node_path(tree: MindmapTree, node_id: str) -> list[dict[str, Any]] | None:
    root = tree.get("root")
    if not isinstance(root, dict):
        return None

    def visit(node: dict[str, Any], path: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        current_path = [*path, node]
        if node.get("id") == node_id:
            return current_path
        children = node.get("children")
        if not isinstance(children, list):
            return None
        for child in children:
            if isinstance(child, dict):
                result = visit(child, current_path)
                if result:
                    return result
        return None

    return visit(root, [])


def count_nodes(tree: MindmapTree) -> int:
    root = tree.get("root")
    if not isinstance(root, dict):
        return 0

    def count(node: dict[str, Any]) -> int:
        children = node.get("children")
        return 1 + sum(count(child) for child in children if isinstance(child, dict)) if isinstance(children, list) else 1

    return count(root)


def _normalize_children(
    raw_children: list[Any],
    doc_id: str,
    parent_id: str,
    depth: int,
    max_depth: int,
    node_budget: int,
    id_prefix: str,
) -> list[dict[str, Any]]:
    if depth > max_depth or node_budget <= 0:
        return []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_children:
        if node_budget <= 0 or len(result) >= MAX_CHILDREN:
            break
        if isinstance(raw, str):
            item = {"title": raw, "children": []}
        elif isinstance(raw, dict):
            item = raw
        else:
            continue
        title = _clean_label(item.get("title") or item.get("label"), "", max_len=MAX_LABEL_LEN)
        if not title or title in seen:
            continue
        seen.add(title)
        child_id = f"{id_prefix}-{len(result)}"
        grandchildren_raw = item.get("children") if isinstance(item.get("children"), list) else []
        grandchildren = _normalize_children(
            grandchildren_raw,
            doc_id=doc_id,
            parent_id=child_id,
            depth=depth + 1,
            max_depth=max_depth,
            node_budget=node_budget - 1,
            id_prefix=child_id,
        )
        node = _node(
            node_id=child_id,
            title=title,
            depth=depth,
            order=len(result),
            children=grandchildren,
            doc_id=doc_id,
            raw=item,
        )
        node["parent_id"] = parent_id
        result.append(node)
        node_budget -= count_node_dict(node)
    return result


def count_node_dict(node: dict[str, Any]) -> int:
    children = node.get("children")
    return 1 + sum(count_node_dict(child) for child in children if isinstance(child, dict)) if isinstance(children, list) else 1


def _node(
    node_id: str,
    title: str,
    depth: int,
    order: int,
    children: list[dict[str, Any]],
    doc_id: str,
    raw: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": node_id,
        "title": title,
        "summary": _clean_summary(raw.get("summary") or raw.get("note")),
        "depth": depth,
        "order": order,
        "type": _clean_type(raw.get("type")),
        "expandable": bool(children) or depth < MAX_EXPAND_DEPTH,
        "children_loaded": bool(children),
        "children": children,
        "source_refs": _source_refs(raw, default_doc_id=doc_id),
    }


def _clean_label(value: Any, fallback: str, max_len: int) -> str:
    text = str(value or fallback or "").strip()
    text = re.sub(r"^[#\-\*\d\.\s]+", "", text)
    text = text.replace("**", "").replace("`", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def _clean_summary(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return re.sub(r"\s+", " ", text)[:180]


def _clean_type(value: Any) -> str:
    allowed = {"concept", "process", "example", "pitfall", "comparison", "formula", "application", "summary"}
    text = str(value or "concept").strip()
    return text if text in allowed else "concept"


def _source_refs(raw: Any, default_doc_id: str | None = None) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    refs = raw.get("source_refs") or raw.get("sources") or []
    if not isinstance(refs, list):
        return []
    result: list[dict[str, Any]] = []
    for ref in refs[:4]:
        if isinstance(ref, dict):
            page_num = _int_or_none(ref.get("page_num") or ref.get("page"))
            chunk_index = _int_or_none(ref.get("chunk_index"))
            label = str(ref.get("label") or "").strip()[:40] or None
            result.append(
                {
                    "doc_id": str(ref.get("doc_id") or default_doc_id or ""),
                    "page_num": page_num,
                    "chunk_index": chunk_index,
                    "label": label,
                }
            )
        elif isinstance(ref, str):
            result.append({"doc_id": default_doc_id or "", "page_num": _page_from_text(ref), "chunk_index": None, "label": ref[:40]})
    return result


def _parse_markdown_line(line: str) -> tuple[int, str] | None:
    raw = line.rstrip()
    if not raw.strip() or raw.strip().startswith("```"):
        return None
    heading_match = re.match(r"^(#{1,6})\s+(.+)$", raw.strip())
    if heading_match:
        return len(heading_match.group(1)), _clean_label(heading_match.group(2), "", max_len=MAX_LABEL_LEN)
    bullet = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.+)$", raw)
    if bullet:
        return 2 + len(bullet.group(1)) // 2, _clean_label(bullet.group(3), "", max_len=MAX_LABEL_LEN)
    return None


def _safe_tree(content: str) -> MindmapTree | None:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) and isinstance(parsed.get("root"), dict) else None


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _page_from_text(value: str) -> int | None:
    match = re.search(r"(?:p\.?|第)\s*(\d+)", value, re.IGNORECASE)
    return int(match.group(1)) if match else None
