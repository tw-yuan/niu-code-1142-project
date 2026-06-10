# 新系統：NotebookLM 學業輔助系統 規劃

## Context

使用者想打造全新的 Python 學業輔助系統，讓學生上傳講義後，系統自動分析內容並提出幾個學習方向供選擇，進而進行互動問答或學習。

舊系統（project.md / agents.md）是「作業草稿生成」為核心，此次全新開始，不延伸舊程式碼。

**使用者確認的設計決策：**
- UI：Web App（FastAPI + React）
- 方向卡片：固定通用選項 + LLM 動態生成的講義專屬選項（兩者都有）
- RAG 策略：混合模式 — 短文全文傳入、長文用 RAG 向量搜尋
- 帳號：多人共用密碼登入（延續舊系統模式）

---

## 系統架構

### 核心使用流程

```
登入（暱稱 + 共用密碼）
  ↓
上傳講義（PDF / DOCX / PPTX / TXT / MD / JPG / PNG / WebP）
  ↓
系統解析 + 分析內容（loading 動畫）
  ↓
顯示方向卡片：
  [固定 4 張] 深入問答 / 章節摘要 / 觀念解釋 / 自我測驗
  [動態 2-3 張] LLM 根據講義內容與課程脈絡生成的客製化方向
  ↓
使用者點選方向
  ↓
進入互動學習介面（串流聊天）
  ↓
歷史記錄頁面可查閱過去對話
```

### Tech Stack

| 層級 | 技術 |
|------|------|
| Backend | Python 3.12 + FastAPI + SQLAlchemy |
| Database | SQLite（MVP），可升級 PostgreSQL |
| LLM | OpenAI-compatible（OpenRouter） |
| Embeddings | text-embedding-3-small |
| Vector DB | ChromaDB（embedded，無需額外伺服器） |
| 串流 | SSE via FastAPI StreamingResponse |
| Frontend | React 18 + Vite + Tailwind CSS |
| 部署 | Docker Compose |

---

## 資料模型（SQLAlchemy + SQLite）

```
User         — nickname, created_at
Session      — user_id, token, expires_at
Document     — user_id, filename, original_filename, file_type,
               parsed_text, token_count, index_status (pending/indexed/failed),
               created_at
LearningSession — user_id, document_id, direction_key, direction_label,
                  created_at
ChatMessage  — session_id, role (user/assistant), content,
               context_chunks_used (JSON), created_at
SystemSetting — key, value, encrypted_value
```

ChromaDB collection 儲存 `DocumentChunk`（每份文件的向量化段落），不進 SQLite。

---

## 目錄結構

```
notebooklm-app/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py               # env 設定
│   │   ├── database.py             # SQLAlchemy engine / session
│   │   ├── deps.py                 # FastAPI dependency injection
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── session.py
│   │   │   ├── document.py
│   │   │   ├── learning_session.py
│   │   │   ├── chat_message.py
│   │   │   └── system_setting.py
│   │   ├── routers/
│   │   │   ├── auth.py             # POST /login, /logout, GET /me
│   │   │   ├── documents.py        # CRUD + /directions endpoint
│   │   │   └── sessions.py         # 學習 session + 聊天
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── document_service.py # 解析 + token 計算
│   │   │   ├── rag_service.py      # ChromaDB 初始化、chunk/embed/store、search
│   │   │   ├── direction_service.py # 固定方向 + LLM 動態方向
│   │   │   └── chat_service.py     # 建構 context + SSE 串流
│   │   └── utils/
│   │       ├── file_parsers.py     # PDF/DOCX/PPTX/TXT/MD/圖片 解析
│   │       └── security.py        # 密碼驗證、session token
│   ├── data/                       # 上傳檔案 + ChromaDB 資料夾
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   ├── client.ts           # axios instance
│   │   │   ├── auth.ts
│   │   │   ├── documents.ts
│   │   │   └── sessions.ts
│   │   ├── auth/
│   │   │   ├── SessionContext.tsx
│   │   │   └── RequireAuth.tsx
│   │   ├── components/
│   │   │   ├── DirectionCard.tsx   # 方向卡片（固定 vs 動態標示）
│   │   │   ├── ChatBubble.tsx
│   │   │   ├── FileUploader.tsx
│   │   │   └── AppHeader.tsx
│   │   └── pages/
│   │       ├── LoginPage.tsx
│   │       ├── HomePage.tsx        # 文件列表 + 上傳入口
│   │       ├── DocumentPage.tsx    # 分析結果 + 方向選擇
│   │       ├── ChatPage.tsx        # 互動學習介面
│   │       └── HistoryPage.tsx
│   └── package.json
├── docker-compose.yml
└── .env.example
```

---

## 各服務關鍵設計

### RAG 策略（rag_service.py）

- **閾值**：12,000 tokens（約 50 頁講義）
- **短文件**（< 12K tokens）：全文直接放入 LLM context
- **長文件**（≥ 12K tokens）：ChromaDB 語意搜尋，取 top-5 相關段落
- **Chunk 大小**：500 tokens，50 token overlap
- **Embedding 模型**：`text-embedding-3-small`

```python
# rag_service.py 核心邏輯
def get_context(document: Document, query: str) -> str:
    if document.token_count < 12000:
        return document.parsed_text
    chunks = chroma_collection.query(query_texts=[query], n_results=5)
    return "\n\n---\n\n".join(chunks["documents"][0])
```

### 方向系統（direction_service.py）

**固定方向**（4 張，每次都顯示）：
- `qa` 💬 深入問答 — 針對任何問題自由提問
- `summary` 📝 章節摘要 — 生成各章節重點摘要
- `explain` 🧠 觀念解釋 — 解釋課程中的重要概念
- `quiz` 📋 自我測驗 — 生成測驗題目並即時批改

**動態方向**（2-3 張，LLM 生成）：
- 讀取文件前 3000 字 + 選填課程名稱 / 本週主題 / 學習目標
- 請 LLM 以 JSON 回傳 2-3 個客製化學習方向
- 格式：`{key, label, description, emoji}`
- 範例：「資料結構演算法練習」、「微積分公式整理」、「化學反應方程式解題」

### Chat 串流（chat_service.py）

```
POST /api/sessions/{id}/messages
  → 取得 document context（全文 or RAG）
  → 組合 system prompt（依 direction 不同）
  → 呼叫 LLM API（streaming=True）
  → SSE 逐 token 推送給前端
  → 完成後儲存 ChatMessage 記錄
```

### System Prompt 依方向變化

| Direction | System Prompt 重點 |
|-----------|-------------------|
| qa | 自由問答，嚴格基於提供的講義內容回答 |
| summary | 系統化整理各章節，條列重點 |
| explain | 深入解釋概念，舉例說明，連結相關知識 |
| quiz | 出題、等待使用者回答、給予評分與解析 |
| 動態方向 | LLM 生成時一併附上 system prompt hint |

---

## API 端點總覽

```
POST /api/auth/login          # 暱稱 + 共用密碼
POST /api/auth/logout
GET  /api/auth/me

POST /api/documents/upload    # multipart/form-data
GET  /api/documents           # 列出使用者的文件
GET  /api/documents/{id}
DELETE /api/documents/{id}
GET  /api/documents/{id}/directions   # 回傳固定+動態方向（SSE or 一次回傳）

POST /api/sessions            # {document_id, direction_key, direction_label}
GET  /api/sessions            # 列出使用者學習 sessions
GET  /api/sessions/{id}       # 含完整 chat history
DELETE /api/sessions/{id}

POST /api/sessions/{id}/messages  # {content} → SSE 串流 LLM 回覆
```

---

## 前端頁面設計

### DocumentPage（核心頁面）
```
┌─────────────────────────────────────────┐
│ [文件名稱]   [解析中... / 已完成]         │
├─────────────────────────────────────────┤
│ 通用學習方向                              │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │ 💬 深入   │ │ 📝 章節   │ │ 🧠 觀念  │ │
│ │  問答    │ │  摘要    │ │  解釋   │ │
│ └──────────┘ └──────────┘ └──────────┘ │
│ ┌──────────┐                            │
│ │ 📋 自我   │                            │
│ │  測驗    │                            │
│ └──────────┘                            │
├─────────────────────────────────────────┤
│ ✨ 專為這份講義推薦                        │
│ ┌──────────────┐ ┌──────────────┐       │
│ │ [動態方向 1] │ │ [動態方向 2] │       │
│ └──────────────┘ └──────────────┘       │
└─────────────────────────────────────────┘
```

### ChatPage
- 左欄：文件資訊 + 方向標示
- 右欄：對話介面，串流打字效果
- 底部：輸入框 + 送出按鈕

---

## 里程碑（建議順序）

| 里程碑 | 內容 |
|--------|------|
| M1 | 專案骨架 + 環境設定 + Auth + DB schema |
| M2 | 文件上傳 + 解析（PDF/DOCX/PPTX/TXT/MD/圖片）+ token 計算 |
| M3 | RAG pipeline（ChromaDB + embedding + chunk）|
| M4 | 方向生成（固定 + LLM 動態）|
| M5 | Chat 串流（SSE + system prompt + context 組裝）|
| M6 | Frontend：登入 + 首頁 + 文件頁（方向卡片）|
| M7 | Frontend：聊天介面（串流打字）|
| M8 | 歷史記錄（sessions 列表、舊對話）|
| M9 | Docker 打包 + .env.example + 整合測試 |

---

## 驗收確認清單

- [ ] 上傳 PDF 講義後成功解析並顯示 token 數
- [ ] 短文件（< 12K tokens）直接全文對話正常
- [ ] 長文件（≥ 12K tokens）RAG 搜尋找到相關段落
- [ ] 動態方向卡片顯示與講義內容相關
- [ ] 四種固定方向各自觸發不同 system prompt 行為
- [ ] 聊天回覆有串流打字效果
- [ ] 歷史頁面可看到過去的 session 與對話
- [ ] 多人以共用密碼登入後資料隔離正常
- [ ] Docker Compose 一鍵啟動

---

## 關鍵依賴套件

```toml
# backend/pyproject.toml
fastapi, uvicorn[standard]
sqlalchemy, aiosqlite
python-multipart           # 檔案上傳
PyMuPDF                    # PDF 解析
python-docx                # DOCX 解析
python-pptx                # PPTX 解析
tiktoken                   # token 計算
openai                     # LLM + embeddings
chromadb                   # 向量資料庫
python-jose[cryptography]  # session token
passlib[bcrypt]            # 密碼 hash
httpx                      # async HTTP（測試用）
```

```json
// frontend/package.json 關鍵套件
"react", "react-router-dom", "axios", "tailwindcss"
```
