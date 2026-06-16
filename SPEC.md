# LearnAI — 學習輔助平台 Project Specification

> 版本：v3.0.0
> 最後更新：2026-06-16
> 作者：Yuan

---

## 1. 專案概述

LearnAI 是一套多租戶 AI 學習輔助平台。學生上傳課程資料（PDF、Markdown、PPTX、DOCX），系統透過 Vision LLM 進行 OCR 解析並向量化，提供 RAG 問答（Streaming）、自動摘要、測驗生成、心智圖、閃卡複習等功能。

**核心定位**：Python 課程期末專案，Python 為主要語言，線上部署展示。

---

## 2. 技術選型總覽

| 層級 | 技術 | 說明 |
|------|------|------|
| 後端框架 | FastAPI 0.111+ | Python 3.12，原生 async，自動 OpenAPI 文件 |
| 任務佇列 | Celery 5 + Redis | 非同步文件處理 |
| 向量資料庫 | ChromaDB | Pure Python，本地 SQLite 後端，無需額外 container |
| 關聯資料庫 | SQLite（開發）/ PostgreSQL（生產）| SQLAlchemy 2.0 async ORM |
| 檔案儲存 | Local filesystem（`./data/`） | 無需外部物件儲存服務 |
| 快取／佇列 | Redis 7 | Celery broker + WebSocket pub/sub |
| LLM | OpenAI-compatible API | Chat、Embedding、Vision 統一接口，全面支援 Streaming |
| OCR 策略 | Vision LLM（GPT-4o）| 每頁轉 PNG 後送 Vision API 萃取文字 |
| 前端框架 | React 18 + Vite 5 | TypeScript |
| UI 元件庫 | shadcn/ui + Tailwind CSS v4 | 簡潔淺色現代風，icon 用 Lucide，禁用 emoji |
| 容器化 | Docker Compose | 3 個 container：backend（含 ChromaDB）、redis、frontend |

---

## 3. 設計原則

| 原則 | 說明 |
|------|------|
| Python First | 所有後端邏輯以 Python 實作，ChromaDB 直接 in-process 執行 |
| Streaming First | 所有 LLM 回應均以 Streaming 方式傳遞，不等待完整回應才顯示 |
| 多租戶隔離 | 每位使用者的檔案、向量、對話完全隔離 |
| LLM 後端無鎖定 | OpenAI-compatible 格式，可替換 GPT-4o / Gemini / Ollama 等 |
| 本地儲存 | 檔案與向量 DB 均存於 `./data/`，無需外部服務 |
| 視覺風格 | 淺色、簡潔、現代；禁止 emoji；使用 Lucide icon |

---

## 4. Docker Compose 架構

```
services:
  backend:    FastAPI + Celery Worker + ChromaDB（in-process）
  redis:      Redis 7（Celery broker + WebSocket pub/sub）
  frontend:   Vite build → Nginx static serve
```

ChromaDB 以 Python library 形式直接在 backend process 內執行，資料存於 `./data/chroma/`，**完全不需要額外 container**。

> 注意：Celery Worker 與 FastAPI 共用同一個 Docker image，但以不同 entrypoint 啟動。兩者都能存取 `./data/` volume 與 ChromaDB。

---

## 5. 使用者角色

### 5.1 學生（Student）
- 以 username / email / password 自助註冊
- 上傳與管理個人文件
- 使用所有 AI 學習功能
- 查看個人 token 使用量

### 5.2 平台管理員（Admin）
- 同樣以 username / email / password 登入（`role` 欄位區分）
- 第一個註冊帳號自動成為 admin，或透過 CLI 指令提權
- 管理所有使用者（修改配額、停用帳號）
- 設定全域 LLM 後端（API Base URL、Key、Model）
- 查看系統統計

---

## 6. 認證系統

### 6.1 註冊
- 欄位：`username`（唯一）、`email`（唯一）、`password`
- 密碼以 bcrypt hash 儲存
- 預設角色：`student`；第一個帳號自動設為 `admin`

### 6.2 登入
- 支援 username 或 email 登入
- 回傳 JWT Access Token（15 分鐘）+ Refresh Token（7 天，httpOnly cookie）
- Refresh Token rotation：每次刷新換發新 token

### 6.3 端點
```
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

---

## 7. Streaming 規格

### 7.1 所有 LLM 回應均為 Streaming

不論是 RAG 問答、摘要生成、測驗題目生成、心智圖生成，所有呼叫 LLM 的功能一律採用 **Server-Sent Events（SSE）** 串流回應。前端不需等待完整結果，字元逐步顯示。

### 7.2 SSE 訊息格式規範

所有 SSE 端點使用統一訊息格式：

```
# 內容片段（逐 token）
data: {"type": "chunk", "content": "這是"}

data: {"type": "chunk", "content": "一段"}

data: {"type": "chunk", "content": "回應"}

# 功能特定的附加資料（在串流結束前送出）
data: {"type": "citations", "data": [{"doc_id": "...", "filename": "...", "page": 3}]}

data: {"type": "quiz_meta", "data": {"quiz_id": "...", "question_count": 10}}

# 結束符號
data: [DONE]
```

### 7.3 各功能的 SSE 端點

| 功能 | 端點 | 額外 event type |
|------|------|----------------|
| RAG 問答 | `POST /chat/sessions/{id}/message` | `citations` |
| 摘要生成 | `POST /summary/stream` | `summary_meta` |
| 測驗生成 | `POST /quiz/stream` | `quiz_meta`（含 quiz_id 供後續存取） |
| 心智圖生成 | `POST /mindmap/stream` | `mindmap_meta` |
| 閃卡生成 | `POST /flashcards/stream` | `flashcard_meta` |

### 7.4 前端 Streaming 消費規範

```typescript
// 統一的 stream consumer
async function* consumeStream(response: Response): AsyncGenerator<StreamEvent> {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n\n")
    buffer = lines.pop() ?? ""
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue
      const raw = line.slice(6).trim()
      if (raw === "[DONE]") return
      yield JSON.parse(raw) as StreamEvent
    }
  }
}

// 使用範例
for await (const event of consumeStream(response)) {
  if (event.type === "chunk") {
    setContent(prev => prev + event.content)
  } else if (event.type === "citations") {
    setCitations(event.data)
  }
}
```

### 7.5 錯誤處理（Streaming 中發生錯誤）

```
data: {"type": "error", "code": "llm_unavailable", "message": "AI 服務暫時無法使用"}

data: [DONE]
```

前端收到 `type: "error"` 時停止消費並顯示錯誤提示，不拋出例外。

---

## 8. 文件處理 Pipeline

### 8.1 支援格式

| 格式 | 轉圖片方式 | OCR |
|------|-----------|-----|
| PDF | PyMuPDF（每頁 150 DPI PNG） | Vision LLM |
| PPTX | LibreOffice headless → PDF → PyMuPDF | Vision LLM |
| DOCX | LibreOffice headless → PDF → PyMuPDF | Vision LLM |
| Markdown | 直接讀取文字 | 不需要 |

### 8.2 文件狀態機

```
uploading → converting → ocr_processing → embedding → ready
                                                     ↘ error
```

### 8.3 完整流程

```
使用者上傳檔案
  → 驗證（格式白名單、大小限制）
  → 儲存原始檔案：./data/uploads/{user_id}/{doc_id}/original.{ext}
  → 建立 DB 記錄（status: uploading）
  → 觸發 Celery 任務 process_document
      ├── [converting] 轉換為 PNG 圖片
      │     → 儲存至 ./data/uploads/{user_id}/{doc_id}/pages/page_NNN.png
      ├── [ocr_processing] Vision OCR（逐頁，有快取）
      │     → 結果快取至 ./data/uploads/{user_id}/{doc_id}/pages/ocr_cache.json
      │     → WebSocket 推播進度（每頁完成更新）
      ├── [embedding] 文字切分 + Embedding
      │     → 呼叫 Embedding API（批次）
      │     → 存入 ChromaDB（collection: "documents"，metadata 含 user_id、doc_id、page_num）
      └── [ready] 更新 DB 狀態
  → WebSocket 推播 doc_ready
```

### 8.4 本地檔案結構

```
./data/
├── uploads/
│   └── {user_id}/
│       └── {doc_id}/
│           ├── original.pdf
│           └── pages/
│               ├── page_001.png
│               ├── page_002.png
│               └── ocr_cache.json   # {page_num: {text, model, cached_at}}
├── chroma/                          # ChromaDB 資料目錄
└── db/
    └── learnai.db                   # SQLite
```

### 8.5 ChromaDB 向量儲存

```python
# 單一 collection，以 metadata filter 實現多租戶隔離
collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"},
)

# 寫入（upsert）
collection.upsert(
    ids=[f"{doc_id}_chunk_{i}" for i in range(len(chunks))],
    embeddings=embeddings,
    documents=[c["text"] for c in chunks],
    metadatas=[{
        "user_id": user_id,
        "doc_id": doc_id,
        "filename": filename,
        "page_num": c["page_num"],
        "chunk_index": c["chunk_index"],
    } for c in chunks],
)

# 查詢（必須帶 user_id filter）
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"user_id": {"$eq": user_id}},   # 多租戶隔離
)
```

### 8.6 限制

| 項目 | 限制 |
|------|------|
| 單檔大小 | 50 MB |
| 每位使用者總儲存 | 500 MB |
| 每份文件最大頁數 | 100 頁（超過截斷並提示）|
| 同時處理中任務 | 3 個/使用者 |

---

## 9. 功能規格

### 9.1 RAG 問答（Streaming）

```
使用者問題
  → Query Rewriting（LLM 改寫，非 Streaming）
  → ChromaDB 向量搜尋（top-5，帶 user_id filter）
  → 組裝 Prompt：system + 對話歷史 + 檢索段落 + 問題
  → 呼叫 LLM（Streaming）
  → SSE 推送 chunk events
  → 串流結束後送出 citations event
  → 儲存完整對話到 DB
```

對話模式：嚴格（僅引用文件）/ 增強（可補充背景知識）/ 蘇格拉底（引導式追問）

### 9.2 摘要（Streaming）

| 類型 | 說明 |
|------|------|
| 全文摘要 | 300–500 字，Map-Reduce 處理長文件 |
| 重點條列 | N 個要點（預設 10 條）|
| 考前速覽 | 強調定義、公式、比較 |

長文件（>8000 tokens）分批送入 LLM，每批摘要串流給前端，最終合併再送一次最終摘要串流。

### 9.3 測驗生成（Streaming）

題型：單選（MC）、多選（MSQ）、是非（TF）、填空（Fill）、簡答（SA）

LLM 以 JSON 格式生成題目，串流方式輸出。前端收到 `quiz_meta`（含 `quiz_id`）後，使用者可進入作答頁面。

### 9.4 心智圖（Streaming）

LLM 生成 Markmap 相容的階層式 Markdown，串流輸出。前端逐步接收 Markdown 並即時更新 Markmap.js 渲染結果（使用者可看到心智圖逐漸長出來）。

### 9.5 閃卡（Streaming）

LLM 串流生成問題-答案對，前端即時顯示已生成的閃卡清單。使用 SM-2 演算法管理複習排程。

### 9.6 解釋等級

| 等級 | 說明 |
|------|------|
| ELI5 | 比喻與故事，適合完全初學者 |
| 高中生 | 避免數學推導 |
| 大學生 | 標準學術解釋（預設）|
| 專家 | 嚴格定義 + 延伸方向 |

回應以 Streaming 輸出。

### 9.7 蘇格拉底導師

AI 不直接給答案，透過追問引導學生思考。學生可按「給我提示」或「直接告訴我」切換模式。所有回應 Streaming 輸出。

### 9.8 學習進度儀表板

- 本週學習時間
- 文件處理狀態一覽
- 測驗歷史分數趨勢（Recharts）
- 閃卡複習連續天數（Streak）
- 錯題率最高的 Top 5 概念

---

## 10. 系統架構圖

```
瀏覽器
  React 18 + Vite（TypeScript）
  shadcn/ui + Tailwind CSS v4
  Zustand │ Markmap.js │ Recharts
     │
     ├── HTTP（REST）
     ├── SSE（Streaming LLM 回應）
     └── WebSocket（文件處理進度）
     │
┌────▼─────────────────────────────────────┐
│  backend container                        │
│                                           │
│  FastAPI（Uvicorn）                       │
│    /auth /documents /chat /quiz           │
│    /summary /mindmap /flashcards /admin   │
│                                           │
│  ChromaDB（in-process）                   │
│    └── ./data/chroma/                     │
│                                           │
│  SQLite / PostgreSQL                      │
│    └── ./data/db/learnai.db               │
└────────────────┬─────────────────────────┘
                 │ Celery tasks
┌────────────────▼─────────────────────────┐
│  worker container（同 image，不同 CMD）   │
│    process_document task                  │
│      → LibreOffice → PyMuPDF → OCR       │
│      → Chunking → Embedding → ChromaDB   │
└────────────────┬─────────────────────────┘
                 │
┌────────────────▼──────┐   ┌─────────────────────────┐
│  redis container       │   │  LLM API（外部）         │
│  Celery broker         │   │  OpenAI-compatible       │
│  WebSocket pub/sub     │   │  Chat / Vision / Embed   │
└────────────────────────┘   └─────────────────────────┘
```

---

## 11. 資料庫 Schema

```sql
CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'student',
    quota_mb      INTEGER NOT NULL DEFAULT 500,
    token_quota   INTEGER NOT NULL DEFAULT 1000000,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE documents (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename    TEXT NOT NULL,
    file_type   TEXT NOT NULL,
    file_size   INTEGER NOT NULL,
    local_path  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'uploading',
    page_count  INTEGER,
    chunk_count INTEGER,
    error_msg   TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE chat_sessions (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT,
    doc_ids    TEXT NOT NULL DEFAULT '[]',
    mode       TEXT NOT NULL DEFAULT 'enhanced',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE chat_messages (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    citations   TEXT NOT NULL DEFAULT '[]',
    token_count INTEGER,
    created_at  TEXT NOT NULL
);

CREATE TABLE quizzes (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    doc_ids    TEXT NOT NULL DEFAULT '[]',
    config     TEXT NOT NULL,
    questions  TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE quiz_attempts (
    id           TEXT PRIMARY KEY,
    quiz_id      TEXT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    answers      TEXT NOT NULL,
    total_score  REAL,
    duration_sec INTEGER,
    completed_at TEXT NOT NULL
);

CREATE TABLE flashcards (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    doc_id        TEXT REFERENCES documents(id) ON DELETE CASCADE,
    front         TEXT NOT NULL,
    back          TEXT NOT NULL,
    source_page   INTEGER,
    repetition    INTEGER NOT NULL DEFAULT 0,
    ease_factor   REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 1,
    next_review   TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE token_usage (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    feature     TEXT NOT NULL,
    tokens_used INTEGER NOT NULL,
    model       TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE admin_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

## 12. API 端點規格

### 認證
```
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

### 文件
```
POST   /documents/upload
GET    /documents
GET    /documents/{id}
DELETE /documents/{id}
GET    /documents/{id}/status
GET    /documents/{id}/pages/{page_num}   # 取得頁面圖片（inline preview）
```

### 對話（Streaming SSE）
```
POST   /chat/sessions
GET    /chat/sessions
GET    /chat/sessions/{id}
DELETE /chat/sessions/{id}
POST   /chat/sessions/{id}/message        # SSE streaming
```

### 摘要（Streaming SSE）
```
POST /summary/stream                      # SSE streaming
GET  /summary/{doc_id}                    # 取得已快取的摘要
```

### 測驗（Streaming SSE）
```
POST   /quiz/stream                       # SSE streaming 生成題目
GET    /quiz
GET    /quiz/{id}
POST   /quiz/{id}/attempt
GET    /quiz/{id}/attempts
GET    /quiz/wrongbook
```

### 心智圖（Streaming SSE）
```
POST /mindmap/stream                      # SSE streaming
GET  /mindmap/{doc_id}
PUT  /mindmap/{id}
```

### 閃卡（Streaming SSE）
```
POST   /flashcards/stream                 # SSE streaming 生成閃卡
GET    /flashcards
POST   /flashcards
PUT    /flashcards/{id}
DELETE /flashcards/{id}
POST   /flashcards/{id}/review
```

### 管理員
```
GET  /admin/users
PUT  /admin/users/{id}
GET  /admin/stats
GET  /admin/config
PUT  /admin/config
```

### WebSocket
```
WS /ws                                    # ?token=<jwt>，文件處理進度推播
```

---

## 13. LLM 整合規格

### 13.1 設定結構（admin_config 表）

```json
{
  "chat": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "model": "gpt-4o-mini",
    "max_tokens": 4096,
    "temperature": 0.3
  },
  "vision": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "model": "gpt-4o",
    "max_tokens": 2048
  },
  "embedding": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "model": "text-embedding-3-small",
    "dimensions": 1536
  }
}
```

### 13.2 三種調用模式

| 模式 | 說明 | Streaming |
|------|------|-----------|
| Chat | 一般文字對話 | 必須支援 |
| Vision | 圖片 OCR | 不需要（逐頁批次）|
| Embedding | 向量化文字 | 不需要（批次）|

### 13.3 OCR 快取

```json
// ./data/uploads/{user_id}/{doc_id}/pages/ocr_cache.json
{
  "1": {"text": "第一頁內容...", "model": "gpt-4o", "cached_at": "2026-06-16T..."},
  "2": {"text": "第二頁內容...", "model": "gpt-4o", "cached_at": "2026-06-16T..."}
}
```

---

## 14. 安全性規格

| 項目 | 做法 |
|------|------|
| 密碼 | bcrypt（cost 12）|
| JWT | HS256，secret 從環境變數讀取 |
| 多租戶隔離 | DB query 強制帶 `user_id`；ChromaDB `where={"user_id": ...}` |
| 檔案存取 | 只透過 API 提供，禁止直接 expose `./data/` 目錄 |
| 路徑安全 | 所有本地路徑在操作前驗證 `path.startswith(base_dir)` |
| 上傳驗證 | MIME type + 副檔名白名單 |
| API Rate Limit | 60 req/min/IP（Redis 計數）|
| LLM Key 保護 | 只存於 DB 與環境變數，不在 response 或 log 中出現 |
| Prompt Injection | 使用者輸入只放 user turn，不插入 system prompt |

---

## 15. 前端規格

### 15.1 視覺設計（強制規範）

- 主題：淺色（Light mode 主要，支援 Dark mode）
- 主色：Indigo（`indigo-600`）
- 背景：`zinc-50`，卡片：`white`，邊框：`zinc-200`
- 文字：`zinc-900`（主）、`zinc-500`（次要）
- 禁止 emoji，使用 `lucide-react` icon，行內 `size={16}`，按鈕/標題 `size={20}`
- 圓角：`rounded-lg`，陰影：`shadow-sm`
- 字型：系統字型（`font-sans`），程式碼：`font-mono`

### 15.2 頁面路由

```
/                   → redirect /dashboard（已登入）或 /login
/login
/register
/dashboard          學習儀表板
/documents          文件管理
/documents/:id      文件詳情（含頁面預覽）
/chat               對話列表
/chat/:sessionId    RAG 對話（Streaming）
/quiz               測驗列表
/quiz/generate      生成新測驗（Streaming）
/quiz/:id           作答 / 結果
/quiz/wrongbook     錯題本
/flashcards         閃卡複習（SM-2）
/mindmap/:docId     心智圖（Streaming 生成）
/summary/:docId     摘要（Streaming 生成）
/settings           個人設定
/admin              管理後台（Admin only）
```

### 15.3 Streaming UI 體驗規範

- 生成中顯示游標動畫（`animate-pulse` 的 `|` 符號）
- 生成完成前禁用「重新生成」按鈕
- 生成中途可「停止」（前端關閉 SSE 連線）
- 錯誤時顯示 inline 錯誤訊息，不彈出 modal

---

## 16. 環境變數

```bash
# 必填
SECRET_KEY=          # openssl rand -hex 32
LLM_API_KEY=         # OpenAI 或相容 API Key
DATA_DIR=./data

# 資料庫
DATABASE_URL=sqlite+aiosqlite:///./data/db/learnai.db
CHROMA_PATH=./data/chroma

# Redis
REDIS_URL=redis://redis:6379/0

# LLM 預設（可在 Admin UI 覆蓋）
LLM_BASE_URL=https://api.openai.com/v1
LLM_CHAT_MODEL=gpt-4o-mini
LLM_VISION_MODEL=gpt-4o
LLM_EMBED_MODEL=text-embedding-3-small

# 限制
MAX_UPLOAD_SIZE_MB=50
MAX_PAGES_PER_DOC=100
DEFAULT_USER_QUOTA_MB=500
DEFAULT_TOKEN_QUOTA=1000000

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

## 17. 開發階段規劃

### Phase 1 — 核心基礎（2 週）
- 使用者認證（register / login / JWT）
- 文件上傳 + 本地儲存
- PDF → PNG → Vision OCR → ChromaDB pipeline
- RAG 問答（Streaming SSE）
- WebSocket 文件處理進度
- 前端：登入、文件上傳、基礎對話介面（Streaming 顯示）

### Phase 2 — 學習功能（1.5 週）
- 摘要生成（Streaming）
- 測驗生成與作答（Streaming 生成）
- 閃卡 + SM-2 排程

### Phase 3 — 進階功能（1 週）
- 心智圖 Markmap.js（Streaming 生成、即時渲染）
- 蘇格拉底導師模式
- 解釋等級功能

### Phase 4 — 完善與部署（0.5 週）
- Admin 後台（LLM 設定、使用者管理）
- 學習進度儀表板
- PPTX / DOCX 支援（LibreOffice）
- Docker Compose 生產設定 + 線上部署

---

*此文件應與 AGENTS.md 搭配閱讀。*
