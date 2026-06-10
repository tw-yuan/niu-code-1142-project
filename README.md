# 學業輔助系統（NotebookLM 風格）

讓學生上傳課程講義後，系統自動解析與分析內容，提供多個「學習方向」卡片，
點選後即可針對該份講義進行串流式互動問答、摘要、觀念解釋或自我測驗。

- 上傳格式：PDF / DOCX / PPTX / TXT / MD / JPG / PNG / WebP
- 介面語言：繁體中文（zh-TW）
- 多人共用一組密碼登入，以暱稱區隔各自的資料

> 設計規格詳見 `agents.md`（中文）。`project.md` 為已淘汰的舊版「作業草稿生成」設計，請忽略。

---

## 技術架構

| 層級 | 技術 |
|------|------|
| 後端 | Python 3.12、FastAPI、SQLAlchemy 2.0（async）|
| 資料庫 | SQLite（`backend/data/app.db`）|
| 向量資料庫 | ChromaDB（embedded，存於 `backend/data/chromadb`）|
| LLM | OpenAI-compatible API（預設 OpenRouter）|
| 前端 | React 19、TypeScript、Vite、Tailwind CSS、React Router 7 |
| 串流 | SSE（FastAPI `StreamingResponse`）|
| 部署 | Docker Compose |

後端採嚴格分層：`routers/`（HTTP 與 Pydantic schema）→ `services/`（商業邏輯）
→ `models/`（ORM）/ `utils/`。上傳檔案與向量資料皆存於 `backend/data/`。

---

## 快速開始

### 1. 環境設定

複製 `.env.example` 為 `.env` 並填入設定：

```bash
cp .env.example .env
```

必填項目：

```env
APP_SECRET_KEY=<請改成一段夠長的隨機字串>
SHARED_LOGIN_PASSWORD=student123          # 所有人共用的登入密碼
ADMIN_LOGIN_PASSWORD=admin123             # 管理員登入密碼，正式環境務必更換
APP_ENV=development                       # production 會拒絕預設密碼
COOKIE_SECURE=false                       # HTTPS 部署時改 true

OPENAI_COMPATIBLE_BASE_URL=https://openrouter.ai/api/v1
OPENAI_COMPATIBLE_API_KEY=sk-or-xxxxxxxx  # LLM API 金鑰
OPENAI_COMPATIBLE_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
VISION_MODEL=openai/gpt-4o-mini           # 解析掃描版 PDF 用
DEMO_MODE=false                           # true 時不依賴外部 LLM，使用示範回覆
```

### 2a. 開發模式

一鍵啟動前後端（會先清除佔用的舊程序）：

```bash
./start-dev.sh
# 後端：http://localhost:8002
# 前端：http://localhost:5173
```

或分別啟動：

```bash
# 後端
cd backend
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

# 前端（另開一個終端機）
cd frontend
npm install
npm run dev          # Vite dev server，/api 自動代理到 :8002
```

### 2b. Docker 部署

```bash
docker compose up --build
# 前端：http://localhost:8001
# 後端：http://localhost:8002
```

---

## 連接埠對照

| 情境 | 前端 | 後端 |
|------|------|------|
| `start-dev.sh` / Vite dev | 5173 | 8002 |
| Docker Compose | 8001 | 8002（對應容器內 8000）|

前端在開發模式由 Vite proxy、在 Docker 由 nginx，將 `/api` 轉發到後端。

---

## 使用流程

```
登入（暱稱 + 共用密碼；管理員可用 ADMIN_LOGIN_PASSWORD 登入）
  ↓
上傳講義 → 系統背景解析、計算 token 數、必要時建立向量索引
  ↓
顯示學習方向卡片
  ├─ 固定 4 張：💬 深入問答 / 📝 章節摘要 / 🧠 觀念解釋 / 📋 自我測驗
  └─ 動態 2-3 張：LLM 依講義內容、課程名稱、主題與學習目標客製生成
  ↓
選擇方向 → 進入串流聊天介面
  ↓
歷史記錄頁可查閱過去的對話
```

---

## 運作重點

**文件解析**：PDF 自動判斷類型——純文字 PDF 以 `pymupdf4llm` 轉 Markdown；
掃描版（超過半數頁面文字過少）則逐頁轉圖送 `VISION_MODEL` 辨識。

**RAG 策略**：依文件長度切換。token 數 < 12,000 直接將全文放入 context；
≥ 12,000 才在上傳時切塊（500 token、50 重疊）建索引，問答時用語意搜尋取 top-5 段落。

**學習方向**：固定方向各有專屬 system prompt；動態方向由 LLM 讀取講義開頭與選填課程脈絡生成，
結果快取於文件記錄中（`?refresh=true` 可強制重新生成）。若未設定 API key 或啟用 `DEMO_MODE=true`，
系統會使用示範方向與示範聊天回覆，讓展示主流程可離線完成。

**串流聊天**：透過 SSE 逐 token 推送，回應中的 `<think>...</think>` 思考過程會在前端
折疊顯示。使用者訊息送出即儲存，AI 回覆於串流結束後儲存。

---

## 主要 API

```
POST   /api/auth/login                  # 暱稱 + 共用密碼，未見過的暱稱自動建立使用者
POST   /api/auth/logout
GET    /api/auth/me

POST   /api/documents/upload            # multipart 上傳並解析
GET    /api/documents                   # 列出自己的文件
GET    /api/documents/{id}
DELETE /api/documents/{id}
GET    /api/documents/{id}/directions   # 取得學習方向（含快取，?refresh=true 重生）
POST   /api/documents/{id}/retry        # 重新解析 / 重建索引

POST   /api/sessions                    # 建立學習 session
GET    /api/sessions                    # 列出 session
GET    /api/sessions/{id}               # 含完整對話紀錄
DELETE /api/sessions/{id}
POST   /api/sessions/{id}/messages      # 送出訊息 → SSE 串流回覆

GET    /api/admin/overview              # 管理後台統計
GET    /api/admin/users                 # 管理全部使用者
PATCH  /api/admin/users/{id}            # 調整 student/admin 角色
GET    /api/admin/documents             # 管理全部文件
POST   /api/admin/documents/{id}/retry
DELETE /api/admin/documents/{id}
GET    /api/admin/sessions              # 管理全部學習紀錄
GET    /api/admin/sessions/{id}         # 查看完整對話
DELETE /api/admin/sessions/{id}
```

---

## 專案結構

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 進入點、CORS、router 註冊
│   │   ├── config.py          # pydantic-settings（讀取 ../.env）
│   │   ├── database.py        # async engine、init_db
│   │   ├── deps.py            # 認證相關 dependency
│   │   ├── models/            # SQLAlchemy ORM
│   │   ├── routers/           # auth / documents / sessions
│   │   ├── services/          # auth / document / rag / direction / chat
│   │   └── utils/            # file_parsers、security
│   ├── data/                  # SQLite、ChromaDB、上傳檔案（gitignored）
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── api/               # axios client、各端點封裝
│       ├── auth/              # SessionContext、RequireAuth
│       ├── components/        # DirectionCard、ChatBubble、FileUploader…
│       └── pages/             # Login / Home / Document / Chat / History
├── docker-compose.yml
├── start-dev.sh
└── .env.example
```

---

## 備註

- 本專案目前以 build、lint、compile 與實際操作流程驗證；尚未導入完整自動化測試。
- 登入採共用密碼，資料隔離依賴 `user_id` 過濾；RAG 索引會寫入 `user_id/doc_id` metadata。
- 管理員用同一個登入頁，輸入 `ADMIN_LOGIN_PASSWORD` 後該暱稱會成為 admin，可進入 `/admin` 管理後台。
