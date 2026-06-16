# AGENTS.md — LearnAI 學習輔助平台

> 本文件供 AI coding agent（Claude Code、Cursor 等）理解專案結構、慣例與規範。
> 閱讀後應能在不詢問的情況下完成大多數開發任務。

---

## 0. 快速導覽

| 任務 | 章節 |
|------|------|
| 了解整體架構 | § 1, § 2 |
| 新增 API 端點 | § 3 |
| 實作 Streaming SSE 端點 | § 4 |
| 整合 LLM | § 5 |
| 操作 ChromaDB | § 6 |
| 處理文件 OCR | § 7 |
| 修改資料庫 schema | § 8 |
| 新增 Celery 任務 | § 9 |
| 前端開發 | § 10 |
| 撰寫 Prompt | § 11 |
| 撰寫測試 | § 12 |
| 本地開發環境 | § 13 |
| 常見錯誤處理 | § 14 |

---

## 1. 專案概述與核心規則

### 1.1 這是什麼

多租戶 AI 學習輔助平台。Python 為主要語言（課程期末專案）。學生上傳文件，透過 Vision LLM OCR 解析 + ChromaDB 向量化後，提供 Streaming RAG 問答、摘要、測驗、心智圖、閃卡等功能。

### 1.2 三個不可違反的規則

**規則 1：Streaming First**
所有呼叫 LLM 產生回應的功能，一律使用 SSE Streaming。不允許等待完整回應再回傳。

**規則 2：多租戶隔離**
任何存取使用者資料的操作，必須帶 `user_id` filter。
- SQLite / PostgreSQL：`WHERE user_id = :user_id`
- ChromaDB：`where={"user_id": {"$eq": user_id}}`
- 本地檔案：路徑必須在 `{DATA_DIR}/uploads/{user_id}/` 之下

**規則 3：LLM 調用統一入口**
所有 LLM 調用（Chat、Vision、Embedding）必須透過 `app/services/llm_client.py`。禁止在任何其他地方直接 import openai。

---

## 2. 目錄結構

```
learnai/
├── docker-compose.yml
├── docker-compose.override.yml    # 開發：hot reload
├── docker-compose.prod.yml        # 生產：Nginx
├── .env.example
├── data/                          # 執行時生成（gitignore）
│   ├── uploads/{user_id}/{doc_id}/
│   │   ├── original.{ext}
│   │   └── pages/
│   │       ├── page_001.png
│   │       └── ocr_cache.json
│   ├── chroma/                    # ChromaDB 資料
│   └── db/learnai.db             # SQLite
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py
│       ├── config.py              # Pydantic Settings
│       ├── dependencies.py        # get_current_user, get_db, get_chroma
│       ├── routers/
│       │   ├── auth.py
│       │   ├── documents.py
│       │   ├── chat.py
│       │   ├── summary.py
│       │   ├── quiz.py
│       │   ├── mindmap.py
│       │   ├── flashcards.py
│       │   └── admin.py
│       ├── services/
│       │   ├── llm_client.py      # LLM 統一入口（Chat/Vision/Embed）
│       │   ├── chroma_service.py  # ChromaDB 封裝
│       │   ├── rag_service.py     # 向量搜尋 + Prompt 組裝 + Streaming
│       │   ├── ocr_service.py     # Vision OCR + 快取
│       │   ├── converter.py       # 檔案 → PNG 圖片
│       │   ├── chunker.py         # 文字切分
│       │   ├── storage.py         # 本地檔案讀寫
│       │   ├── ws_manager.py      # WebSocket 推播
│       │   ├── quiz_service.py
│       │   ├── summary_service.py
│       │   ├── mindmap_service.py
│       │   └── flashcard_service.py
│       ├── tasks/
│       │   ├── celery_app.py
│       │   └── document_tasks.py
│       ├── models/
│       │   ├── database.py
│       │   └── tables.py
│       └── prompts/
│           ├── rag_chat.yaml
│           ├── rag_strict.yaml
│           ├── rag_socratic.yaml
│           ├── ocr.yaml
│           ├── summary_full.yaml
│           ├── summary_bullets.yaml
│           ├── quiz_generate.yaml
│           ├── mindmap.yaml
│           └── flashcard_generate.yaml
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── pages/
│       ├── components/
│       │   ├── ui/               # shadcn/ui（不要手動編輯）
│       │   └── app/              # 業務元件
│       ├── lib/
│       │   ├── api.ts            # fetch 封裝
│       │   ├── stream.ts         # SSE consumer
│       │   ├── auth.ts           # token 管理
│       │   └── ws.ts             # WebSocket
│       └── store/
│           ├── auth.ts
│           ├── documents.ts
│           └── chat.ts
└── scripts/
    └── create_admin.py
```

---

## 3. 後端 API 開發規範

### 3.1 Router 層職責

Router 只做：接收 HTTP request → 呼叫 service → 回傳結果。
禁止在 router 寫業務邏輯、直接操作 DB 或直接呼叫 LLM。

```python
# routers/example.py
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user, get_db
from app.services.example_service import ExampleService
from app.models.tables import User
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/example", tags=["example"])

@router.post("/", response_model=ExampleResponse)
async def create_example(
    body: ExampleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ExampleService(db)
    return await svc.create(user_id=current_user.id, data=body)
```

### 3.2 Service 層職責

業務邏輯、DB 操作、LLM 調用。

```python
class ExampleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, item_id: str, user_id: str):
        from sqlalchemy import select, and_
        stmt = select(Example).where(
            and_(Example.id == item_id, Example.user_id == user_id)  # 必須帶 user_id
        )
        obj = (await self.db.execute(stmt)).scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        return obj
```

### 3.3 錯誤碼規範

| Code | 場景 |
|------|------|
| 400 | 請求格式錯誤 |
| 401 | 未登入 / token 失效 |
| 403 | 跨租戶存取 |
| 404 | 資源不存在 |
| 409 | 衝突（如 username 重複）|
| 413 | 檔案過大 |
| 429 | Rate limit |
| 500 | 內部錯誤（LLM 失敗等）|

### 3.4 認證依賴

```python
from app.dependencies import get_current_user, require_admin

current_user: User = Depends(get_current_user)   # 一般使用者
current_user: User = Depends(require_admin)        # Admin 限定
```

### 3.5 非同步規則

所有 route handler 與 service 方法一律 `async def`。同步阻塞操作（PIL、python-pptx、LibreOffice）用 `asyncio.to_thread()`：

```python
result = await asyncio.to_thread(sync_blocking_function, arg1, arg2)
```

---

## 4. Streaming SSE 實作規範

### 4.1 後端 SSE 端點標準寫法

```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import json

router = APIRouter()

@router.post("/chat/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    body: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rag = RAGService(db)

    async def event_stream():
        try:
            # 1. 串流 LLM chunks
            full_content = ""
            async for chunk in rag.stream_answer(session_id, body.content, current_user.id):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # 2. 串流結束後送附加資料
            citations = await rag.get_last_citations()
            yield f"data: {json.dumps({'type': 'citations', 'data': citations})}\n\n"

            # 3. 非同步儲存完整對話（不阻塞串流）
            asyncio.create_task(rag.save_message(session_id, body.content, full_content, citations))

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'code': 'llm_error', 'message': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # 關閉 Nginx 緩衝，確保即時推送
        },
    )
```

### 4.2 各功能的 event types

| 功能 | chunk | 額外 event |
|------|-------|-----------|
| RAG 問答 | 回應文字片段 | `citations` |
| 摘要 | 摘要文字片段 | `summary_meta`（含 summary_id）|
| 測驗生成 | JSON 文字片段 | `quiz_meta`（含 quiz_id）|
| 心智圖 | Markdown 片段 | `mindmap_meta`（含 mindmap_id）|
| 閃卡生成 | JSON 文字片段 | `flashcard_meta`（含 count）|

### 4.3 測驗/心智圖/閃卡的 JSON Streaming 處理

LLM 輸出 JSON 時也用 Streaming，前端先收集所有 chunk 拼成完整 JSON，再解析：

```python
# service 層
async def stream_quiz(self, ...) -> AsyncGenerator[str, None]:
    llm = get_llm_client()
    full_json = ""
    async for chunk in llm.stream_chat(messages, response_format={"type": "json_object"}):
        full_json += chunk
        yield chunk   # 邊串流邊推給前端

    # 串流完成後儲存
    questions = json.loads(full_json)["questions"]
    quiz = await self._save_quiz(user_id, doc_ids, config, questions)
    # quiz_id 透過額外 event 送出（在 router 層處理）
```

---

## 5. LLM 整合規範

### 5.1 LLMClient 介面

```python
# services/llm_client.py

class LLMClient:
    """
    OpenAI-compatible LLM 統一入口。
    設定從 DB admin_config 表讀取（可在 Admin UI 動態更新）。
    """

    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
        feature: str = "chat",
        user_id: str | None = None,
    ) -> str:
        """一次性文字回應（非 Streaming）。用於 Query Rewriting 等短暫調用。"""
        ...

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
        feature: str = "chat",
        user_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming 文字回應。yield 每個 token chunk。"""
        ...

    async def vision(
        self,
        image_base64: str,
        prompt: str,
        user_id: str | None = None,
    ) -> str:
        """Vision OCR（非 Streaming）。image_base64 為 PNG 的 base64 字串。"""
        ...

    async def embed(
        self,
        texts: list[str],
        user_id: str | None = None,
    ) -> list[list[float]]:
        """批次 Embedding。"""
        ...
```

### 5.2 stream_chat 底層實作參考

```python
async def stream_chat(self, messages, ...) -> AsyncGenerator[str, None]:
    config = await self._get_config("chat")
    client = AsyncOpenAI(base_url=config["base_url"], api_key=config["api_key"])

    stream = await client.chat.completions.create(
        model=config["model"],
        messages=messages,
        stream=True,                          # 關鍵：啟用 streaming
        temperature=temperature ?? config.get("temperature", 0.3),
        max_tokens=max_tokens ?? config.get("max_tokens", 4096),
        response_format=response_format,
    )

    total_tokens = 0
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            total_tokens += 1                 # 近似計算
            yield delta

    # 記錄 token 用量
    if user_id:
        await self._record_usage(user_id, feature, total_tokens, config["model"])
```

### 5.3 何時用 chat vs stream_chat

| 場景 | 方法 |
|------|------|
| Query Rewriting（問題改寫） | `chat`（結果短，不需要串流）|
| RAG 問答 | `stream_chat` |
| 摘要生成 | `stream_chat` |
| 測驗/閃卡/心智圖生成 | `stream_chat`（即使是 JSON output）|
| Vision OCR | `vision`（逐頁批次，不需串流）|
| Embedding | `embed`（批次）|

### 5.4 Prompt 載入

```python
# services/prompt_loader.py
import yaml
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def load_prompt(name: str, **kwargs) -> tuple[str, dict]:
    """回傳 (system_prompt_str, llm_config_dict)"""
    data = yaml.safe_load((PROMPTS_DIR / f"{name}.yaml").read_text())
    system = data["system"].format(**kwargs)
    cfg = {k: v for k, v in data.items() if k not in ("system", "version", "description")}
    return system, cfg
```

---

## 6. ChromaDB 操作規範

### 6.1 初始化（在 dependencies.py）

```python
import chromadb
from app.config import settings

_chroma_client: chromadb.ClientAPI | None = None

def get_chroma() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    return _chroma_client

def get_documents_collection(client: chromadb.ClientAPI):
    return client.get_or_create_collection(
        name="documents",
        metadata={"hnsw:space": "cosine"},
    )
```

### 6.2 Upsert（寫入向量）

```python
# services/chroma_service.py

async def upsert_chunks(
    user_id: str,
    doc_id: str,
    filename: str,
    chunks: list[dict],      # [{text, page_num, chunk_index}]
    embeddings: list[list[float]],
) -> None:
    collection = get_documents_collection(get_chroma())
    collection.upsert(
        ids=[f"{doc_id}__chunk_{c['chunk_index']}" for c in chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[{
            "user_id": user_id,       # 多租戶隔離的關鍵欄位
            "doc_id": doc_id,
            "filename": filename,
            "page_num": c["page_num"],
            "chunk_index": c["chunk_index"],
        } for c in chunks],
    )
```

### 6.3 Query（向量搜尋）

```python
async def query_chunks(
    user_id: str,
    query_embedding: list[float],
    doc_ids: list[str] | None = None,   # None = 搜尋該使用者全部文件
    n_results: int = 5,
) -> list[dict]:
    collection = get_documents_collection(get_chroma())

    # 組裝 where filter（一定要帶 user_id）
    where: dict = {"user_id": {"$eq": user_id}}
    if doc_ids:
        if len(doc_ids) == 1:
            where = {"$and": [{"user_id": {"$eq": user_id}}, {"doc_id": {"$eq": doc_ids[0]}}]}
        else:
            where = {"$and": [{"user_id": {"$eq": user_id}}, {"doc_id": {"$in": doc_ids}}]}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    return [
        {
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        }
        for i in range(len(results["documents"][0]))
    ]
```

### 6.4 刪除（文件刪除時清理向量）

```python
async def delete_doc_chunks(user_id: str, doc_id: str) -> None:
    collection = get_documents_collection(get_chroma())
    # ChromaDB 支援 where filter 刪除
    collection.delete(
        where={"$and": [{"user_id": {"$eq": user_id}}, {"doc_id": {"$eq": doc_id}}]}
    )
```

### 6.5 注意事項

- ChromaDB `PersistentClient` 在 Celery Worker 與 FastAPI 共用同一個 `./data/chroma/` 目錄時，需注意**並發寫入**問題。建議 Celery Worker 寫入時使用 `FileLock`（`filelock` 套件），或確保同一份文件的 upsert 是串行的（單一 Celery task）。
- ChromaDB 不支援跨 process 的 client-server 模式（除非用 `HttpClient`），但同一 process 內多 thread 是安全的。

---

## 7. 文件 OCR Pipeline

### 7.1 converter.py 介面

```python
async def convert_to_images(
    file_path: str,
    output_dir: str,
    dpi: int = 150,
) -> list[str]:                # 回傳 PNG 路徑清單（依頁碼排序）
    """
    依副檔名選擇：
    .pdf  → PyMuPDF (fitz)
    .pptx → LibreOffice headless → PDF → PyMuPDF
    .docx → LibreOffice headless → PDF → PyMuPDF
    .md   → 回傳空清單（直接讀文字）
    """
```

LibreOffice headless 指令：
```python
import subprocess
subprocess.run([
    "libreoffice", "--headless", "--convert-to", "pdf",
    "--outdir", tmp_dir, file_path
], check=True, timeout=120)
```

### 7.2 ocr_service.py 介面

```python
async def ocr_document(
    image_paths: list[str],
    cache_path: str,
    user_id: str,
    on_progress: Callable[[int, int], Awaitable[None]] | None = None,
) -> str:
    """
    回傳帶頁碼標記的完整文字：
    === 第 1 頁 ===
    [OCR 內容]

    === 第 2 頁 ===
    ...
    """
    cache = _load_cache(cache_path)
    texts = []
    for i, img_path in enumerate(image_paths, 1):
        page_key = str(i)
        if page_key not in cache:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            text = await llm.vision(b64, load_ocr_prompt(), user_id=user_id)
            cache[page_key] = {"text": text, "model": ..., "cached_at": now_iso()}
            _save_cache(cache_path, cache)
        texts.append(f"=== 第 {i} 頁 ===\n{cache[page_key]['text']}")
        if on_progress:
            await on_progress(i, len(image_paths))
    return "\n\n".join(texts)
```

### 7.3 chunker.py 介面

```python
def chunk_text(
    text: str,               # 帶頁碼標記的全文
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[dict]:             # [{text, page_num, chunk_index}]
    """
    解析 === 第 N 頁 === 標記以追蹤每個 chunk 的來源頁碼。
    chunk 切分以句子為邊界（不在句子中間截斷）。
    """
```

---

## 8. 資料庫規範

### 8.1 ORM 模型

```python
# models/tables.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Text, ForeignKey
import uuid
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

def new_uuid() -> str:
    return str(uuid.uuid4())

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
```

主鍵統一使用字串 UUID（`String` 型態），相容 SQLite 與 PostgreSQL。

### 8.2 Migration（Alembic）

```bash
alembic revision --autogenerate -m "描述變更"
alembic upgrade head
```

開發環境可在 startup event 直接 `create_all`，生產用 Alembic。

### 8.3 常用查詢

```python
from sqlalchemy import select, and_, desc

# 一定要帶 user_id
stmt = (
    select(Document)
    .where(and_(Document.user_id == user_id, Document.status == "ready"))
    .order_by(desc(Document.created_at))
)
docs = (await db.execute(stmt)).scalars().all()

# 單一資源所有權驗證
stmt = select(Document).where(and_(Document.id == doc_id, Document.user_id == user_id))
doc = (await db.execute(stmt)).scalar_one_or_none()
if not doc:
    raise HTTPException(status_code=404, detail="Document not found")
```

---

## 9. Celery 任務規範

### 9.1 process_document 主任務

```python
# tasks/document_tasks.py
from app.tasks.celery_app import celery_app
import asyncio

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document(self, doc_id: str, user_id: str):
    try:
        asyncio.run(_process_async(doc_id, user_id))
    except Exception as exc:
        asyncio.run(_set_error(doc_id, str(exc)))
        raise self.retry(exc=exc)

async def _process_async(doc_id: str, user_id: str):
    from app.services.ws_manager import push_to_user

    # converting
    await _update_status(doc_id, "converting")
    await push_to_user(user_id, {"type": "doc_status", "doc_id": doc_id, "status": "converting"})
    image_paths = await converter.convert_to_images(original_path, pages_dir)

    # ocr_processing
    await _update_status(doc_id, "ocr_processing")
    async def on_progress(current, total):
        pct = int(current / total * 100)
        await push_to_user(user_id, {
            "type": "doc_status", "doc_id": doc_id,
            "status": "ocr_processing", "progress": pct
        })
    full_text = await ocr_service.ocr_document(image_paths, cache_path, user_id, on_progress)

    # embedding
    await _update_status(doc_id, "embedding")
    await push_to_user(user_id, {"type": "doc_status", "doc_id": doc_id, "status": "embedding"})
    chunks = chunker.chunk_text(full_text)
    embeddings = await llm.embed([c["text"] for c in chunks], user_id=user_id)
    await chroma_service.upsert_chunks(user_id, doc_id, filename, chunks, embeddings)

    # ready
    await _update_status(doc_id, "ready", chunk_count=len(chunks), page_count=len(image_paths))
    await push_to_user(user_id, {"type": "doc_ready", "doc_id": doc_id})
```

### 9.2 任務觸發

```python
from app.tasks.document_tasks import process_document
process_document.apply_async(args=[doc.id, current_user.id], countdown=0)
```

---

## 10. 前端開發規範

### 10.1 視覺設計（強制）

```tsx
// 禁止：emoji
<span>📄 文件</span>

// 正確：Lucide icon
import { FileText } from "lucide-react"
<FileText size={16} className="text-zinc-500" />
```

色彩規範：
- 主色：`indigo-600`（按鈕、連結、active 狀態）
- 背景：`zinc-50`（頁面），`white`（卡片）
- 邊框：`zinc-200`
- 文字主：`zinc-900`，次要：`zinc-500`
- 錯誤：`red-600`

### 10.2 SSE Consumer（stream.ts）

```typescript
// lib/stream.ts

export type StreamEvent =
  | { type: "chunk"; content: string }
  | { type: "citations"; data: Citation[] }
  | { type: "quiz_meta"; data: { quiz_id: string } }
  | { type: "mindmap_meta"; data: { mindmap_id: string } }
  | { type: "flashcard_meta"; data: { count: number } }
  | { type: "summary_meta"; data: { summary_id: string } }
  | { type: "error"; code: string; message: string }

export async function* streamFetch(
  url: string,
  body: unknown,
): AsyncGenerator<StreamEvent> {
  const token = localStorage.getItem("access_token")
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? "Request failed")
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split("\n\n")
    buffer = parts.pop() ?? ""
    for (const part of parts) {
      if (!part.startsWith("data: ")) continue
      const raw = part.slice(6).trim()
      if (raw === "[DONE]") return
      yield JSON.parse(raw) as StreamEvent
    }
  }
}
```

### 10.3 Streaming UI 元件

```tsx
// components/app/StreamingText.tsx
import { useEffect, useState } from "react"

interface Props {
  stream: AsyncGenerator<StreamEvent>
  onCitations?: (citations: Citation[]) => void
  onComplete?: (fullText: string) => void
}

export function StreamingText({ stream, onCitations, onComplete }: Props) {
  const [content, setContent] = useState("")
  const [isStreaming, setIsStreaming] = useState(true)

  useEffect(() => {
    let full = ""
    ;(async () => {
      for await (const event of stream) {
        if (event.type === "chunk") {
          full += event.content
          setContent(full)
        } else if (event.type === "citations") {
          onCitations?.(event.data)
        } else if (event.type === "error") {
          // 顯示錯誤（不拋出）
          setContent(prev => prev + `\n\n[錯誤：${event.message}]`)
        }
      }
      setIsStreaming(false)
      onComplete?.(full)
    })()
  }, [stream])

  return (
    <div className="prose prose-zinc max-w-none">
      {content}
      {isStreaming && <span className="animate-pulse">|</span>}
    </div>
  )
}
```

### 10.4 API Client

```typescript
// lib/api.ts
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("access_token")
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })
  if (res.status === 401) {
    const refreshed = await refreshToken()
    if (!refreshed) { window.location.href = "/login"; throw new ApiError(401, "Unauthorized") }
    return apiFetch(path, options)
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new ApiError(res.status, err.detail ?? "Request failed")
  }
  return res.json()
}
```

### 10.5 WebSocket

```typescript
// lib/ws.ts
const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000"

class WSManager {
  private ws: WebSocket | null = null
  private handlers = new Map<string, Set<(data: unknown) => void>>()

  connect(token: string) {
    if (this.ws?.readyState === WebSocket.OPEN) return
    this.ws = new WebSocket(`${WS_BASE}/ws?token=${token}`)
    this.ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      this.handlers.get(msg.type)?.forEach(fn => fn(msg))
    }
    this.ws.onclose = () => setTimeout(() => this.connect(token), 3000)
  }

  on(type: string, handler: (data: unknown) => void) {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set())
    this.handlers.get(type)!.add(handler)
    return () => this.handlers.get(type)?.delete(handler)
  }
}

export const wsManager = new WSManager()
```

---

## 11. Prompt 設計規範

### 11.1 YAML 格式

```yaml
# prompts/rag_chat.yaml
version: "1.0"
description: "RAG 問答主 Prompt（增強模式）"
temperature: 0.2
max_tokens: 2000

system: |
  你是 LearnAI 學習輔助 AI，協助學生理解課程資料。

  規則：
  1. 優先根據以下「參考資料」回答
  2. 資料中沒有的資訊請說明來自你的背景知識
  3. 引用來源使用 [數字] 標示，例如：根據 [1] 的說明...
  4. 使用繁體中文回答，語氣友善清楚

  參考資料：
  {context}
```

### 11.2 各 Prompt 必要變數

| 檔案 | 必要變數 |
|------|---------|
| `rag_chat.yaml` | `{context}` |
| `rag_strict.yaml` | `{context}` |
| `rag_socratic.yaml` | `{context}`, `{question}` |
| `ocr.yaml` | 無 |
| `summary_full.yaml` | `{document_title}` |
| `summary_bullets.yaml` | `{document_title}`, `{count}` |
| `quiz_generate.yaml` | `{types}`, `{count}`, `{difficulty}`, `{context}` |
| `mindmap.yaml` | `{document_title}` |
| `flashcard_generate.yaml` | `{document_title}`, `{count}` |

### 11.3 JSON Output Prompt 規範

```yaml
system: |
  請嚴格按照指定 JSON 格式回傳，不要有任何額外文字或 Markdown 標記。
  ...
```

解析保護：

```python
import json, re

def parse_json_llm(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)
```

---

## 12. 測試規範

### 12.1 後端

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_stream_chat():
    async def _gen(*args, **kwargs):
        for token in ["這是", "測試", "回應"]:
            yield token
    with patch("app.services.llm_client.LLMClient.stream_chat", return_value=_gen()):
        yield

@pytest.fixture
def mock_vision():
    with patch("app.services.llm_client.LLMClient.vision", new_callable=AsyncMock) as m:
        m.return_value = "=== 第 1 頁 ===\n測試 OCR 文字"
        yield m

@pytest.fixture
def mock_embed():
    with patch("app.services.llm_client.LLMClient.embed", new_callable=AsyncMock) as m:
        m.return_value = [[0.1] * 1536]
        yield m
```

每個新功能必須測試：正常流程、跨租戶拒絕（403）、資源不存在（404）、未授權（401）。

### 12.2 SSE 端點測試

```python
async def test_chat_stream(client, auth_headers, mock_stream_chat):
    response = await client.post(
        "/chat/sessions/test-id/message",
        json={"content": "什麼是排序？"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

    # 收集所有 events
    events = []
    for line in response.text.split("\n\n"):
        if line.startswith("data: ") and line != "data: [DONE]":
            events.append(json.loads(line[6:]))

    chunk_events = [e for e in events if e["type"] == "chunk"]
    assert len(chunk_events) > 0
    assert any(e["type"] == "citations" for e in events)
```

---

## 13. 本地開發環境

### 13.1 啟動

```bash
cp .env.example .env
# 填入 LLM_API_KEY 等

docker compose up -d
docker compose logs -f backend worker

# 建立 admin
docker compose exec backend python scripts/create_admin.py
```

### 13.2 Port 對照

| 服務 | Port |
|------|------|
| 前端 | 3000 |
| 後端 API | 8000 |
| API Docs | 8000/docs |
| Redis | 6379 |

（開發模式無 Nginx，無 Qdrant）

### 13.3 常用指令

```bash
# 只重啟後端
docker compose restart backend

# Celery Worker log
docker compose logs -f worker

# 清除 ChromaDB（重新向量化所有文件）
rm -rf ./data/chroma && docker compose restart backend worker

# 清除 OCR 快取（重新 OCR）
find ./data/uploads -name "ocr_cache.json" -delete
```

---

## 14. 常見問題

### 14.1 Streaming 在 Nginx 後面不即時

Nginx 預設會緩衝 proxy response。確保 response header 含：
```python
headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
```
並在 nginx.conf 設定：
```nginx
proxy_buffering off;
```

### 14.2 ChromaDB 並發寫入

Celery Worker 的 `process_document` task 應確保同一份文件的 upsert 不並發執行（預設 Celery task 是串行的，同一 doc_id 不會重複觸發）。若需要多 worker 實例，改用 ChromaDB HTTP server 模式並加 lock。

### 14.3 OCR 結果為空

常見原因：
- 圖片純白（空白頁）：保存空字串，標記為 `ocr_empty`，不中止流程
- Vision API rate limit：LLMClient 內建 exponential backoff（1/2/4/8/16 秒，最多 5 次）
- 圖片過大（>20MB）：轉換時壓低 DPI（150 → 72）

### 14.4 PPTX / DOCX 轉換失敗

確認 Docker image 中已安裝 LibreOffice：
```dockerfile
RUN apt-get update && apt-get install -y libreoffice --no-install-recommends
```
轉換 timeout 設 120 秒，超時視為 error 並回傳友善訊息。

### 14.5 JWT 過期

前端 `apiFetch` 收到 401 自動呼叫 `POST /auth/refresh`（httpOnly cookie 帶 refresh token），刷新失敗則清除 `localStorage` 並導向 `/login`。

---

## 15. 環境變數快速參考

```bash
# 必填
SECRET_KEY=          # openssl rand -hex 32
LLM_API_KEY=
DATA_DIR=./data

# 預設值
DATABASE_URL=sqlite+aiosqlite:///./data/db/learnai.db
CHROMA_PATH=./data/chroma
REDIS_URL=redis://redis:6379/0
LLM_BASE_URL=https://api.openai.com/v1
LLM_CHAT_MODEL=gpt-4o-mini
LLM_VISION_MODEL=gpt-4o
LLM_EMBED_MODEL=text-embedding-3-small
MAX_UPLOAD_SIZE_MB=50
MAX_PAGES_PER_DOC=100
DEFAULT_USER_QUOTA_MB=500
DEFAULT_TOKEN_QUOTA=1000000
ALLOWED_ORIGINS=http://localhost:3000
```

---

## 16. 程式碼風格

```bash
# Python
ruff format .
ruff check .

# TypeScript
npm run lint
npm run format
```

Git commit 格式：
```
feat: 新增 Streaming 摘要生成
fix: 修正 ChromaDB user_id filter 缺失
refactor: 拆分 LLMClient stream_chat 與 chat
docs: 更新 AGENTS.md Streaming 規範
test: 新增 SSE 端點測試
```

---

*如有疑問請查閱 SPEC.md 取得功能層面的詳細規格。*
