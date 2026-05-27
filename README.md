# AI 課業輔助與作業草稿生成系統

一個以 Python FastAPI 為後端、串接 OpenAI-compatible API 的期末專題 Web 系統。使用者可上傳課程資料與作業需求，由 AI 產生可檢視處理過程、可引用來源、可下載成多種格式的課業輔助草稿。

> **定位**：課業輔助、草稿生成、學習整理與人工審核工具，不是自動代寫作業系統。所有輸出皆包含學術誠信聲明與人工確認清單。

---

## 目錄

- [功能總覽](#功能總覽)
- [技術架構](#技術架構)
- [環境需求](#環境需求)
- [快速開始（Docker）](#快速開始docker)
- [本機開發](#本機開發)
- [環境變數說明](#環境變數說明)
- [使用說明](#使用說明)
- [API 端點一覽](#api-端點一覽)
- [專案結構](#專案結構)
- [常見問題](#常見問題)

---

## 功能總覽

| 功能 | 說明 |
|------|------|
| 學生登入 | 暱稱 + 共用密碼，同暱稱可關聯歷史紀錄 |
| 管理者登入 | 獨立密碼，進入後台管理頁面 |
| 課程資料上傳 | 支援 PDF、DOCX、TXT、MD、XLSX、CSV（可選） |
| 作業輸入 | 上傳作業檔案 + 文字敘述（必填）|
| 輸出格式選擇 | 純文字、Word (.docx)、PDF、Excel (.xlsx) |
| AI 生成 | 串接 OpenAI-compatible API，產生結構化草稿 |
| 即時進度 | SSE 即時顯示處理階段 |
| 詳細過程 | 可展開查看檔案解析、需求拆解、引用來源等紀錄 |
| 結果頁 | 複製全文、下載檔案、引用來源、人工確認清單 |
| 歷史紀錄 | 查看 / 刪除過去任務與結果 |
| 後台設定 | API endpoint、模型、溫度、提示詞、檔案限制、測試連線 |
| 學術誠信 | 所有輸出包含提醒聲明，送出前需勾選確認 |

---

## 技術架構

```
┌─────────────────────────────────────────────┐
│              單一容器 / 單一 Port (8000)       │
│                                             │
│   FastAPI ─── /api/*  → API 路由            │
│           ─── /*      → React SPA 靜態檔案   │
│                                             │
│   SQLite          本機檔案儲存               │
│   (data/app.db)   (data/uploads, generated) │
└─────────────────────────────────────────────┘
          │
          ▼
   OpenAI-compatible API（OpenRouter 等）
```

- **後端**：Python 3.12 + FastAPI + SQLAlchemy (async) + SQLite
- **前端**：React 18 + TypeScript + Vite + Tailwind CSS v4
- **AI**：OpenAI-compatible API（預設 OpenRouter）
- **部署**：Docker multi-stage build，單一容器單一 port

---

## 環境需求

### Docker 部署（推薦）

- Docker 20.10+
- Docker Compose v2+

### 本機開發

- Python 3.12+
- Node.js 20+
- npm 9+

---

## 快速開始（Docker）

### 1. 複製專案

```bash
git clone <your-repo-url>
cd niu-code-1142-project
```

### 2. 建立環境變數檔

```bash
cp backend/.env.example backend/.env
```

### 3. 編輯 `backend/.env`

用文字編輯器打開 `backend/.env`，至少需要修改以下設定：

```env
# 安全性（請更換為隨機字串）
APP_SECRET_KEY=請替換成一組隨機亂碼字串

# 學生登入密碼
SHARED_LOGIN_PASSWORD=你想設定的學生密碼

# 管理者登入密碼
ADMIN_PASSWORD=你想設定的管理者密碼

# AI API 設定（以 OpenRouter 為例）
OPENAI_COMPATIBLE_BASE_URL=https://openrouter.ai/api/v1
OPENAI_COMPATIBLE_API_KEY=sk-or-v1-你的API金鑰
OPENAI_COMPATIBLE_MODEL=openai/gpt-4o-mini
```

> **取得 OpenRouter API Key**：至 [openrouter.ai](https://openrouter.ai/) 註冊帳號 → 進入 Keys 頁面 → Create Key。

### 4. 啟動

```bash
docker compose up --build -d
```

### 5. 開啟瀏覽器

```
http://localhost:8000
```

### 停止

```bash
docker compose down
```

### 查看 Log

```bash
docker compose logs -f
```

---

## 本機開發

如果你不想用 Docker，可以直接在本機跑：

### 1. 後端

```bash
cd backend

# 建立虛擬環境（建議）
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# 安裝依賴
pip install -r requirements.txt

# 建立環境變數
cp .env.example .env
# 編輯 .env（參考上方說明）

# 啟動後端（開發模式，自動重載）
uvicorn app.main:app --reload --port 8000
```

### 2. 前端（開發模式）

開另一個終端機：

```bash
cd frontend

# 安裝依賴
npm install

# 啟動開發伺服器（自動 proxy /api 到 localhost:8000）
npm run dev
```

前端開發伺服器預設在 `http://localhost:5173`，API 請求會自動轉發到後端 `:8000`。

### 3. 合併部署（不用 Docker）

如果要在本機用單一 port 跑：

```bash
# 在專案根目錄
./build.sh

# 啟動
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`build.sh` 會 build 前端並複製到 `backend/static/`，然後 FastAPI 同時提供 API 和前端頁面。

---

## 環境變數說明

所有環境變數設定在 `backend/.env`：

| 變數 | 必填 | 預設值 | 說明 |
|------|:----:|--------|------|
| `APP_SECRET_KEY` | ✅ | `change-me` | 應用程式密鑰，用於安全性，請換成隨機字串 |
| `SHARED_LOGIN_PASSWORD` | ✅ | `student123` | 學生共用登入密碼 |
| `ADMIN_PASSWORD` | ✅ | `admin123` | 管理者登入密碼 |
| `OPENAI_COMPATIBLE_BASE_URL` | ✅ | `https://openrouter.ai/api/v1` | AI API 的 base URL |
| `OPENAI_COMPATIBLE_API_KEY` | ✅ | *(空)* | AI API Key（例如 OpenRouter Key） |
| `OPENAI_COMPATIBLE_MODEL` | ✅ | `openai/gpt-4o-mini` | 使用的模型名稱 |
| `DATABASE_URL` | | `sqlite+aiosqlite:///./data/app.db` | 資料庫連線字串 |
| `UPLOAD_DIR` | | `./data/uploads` | 上傳檔案儲存路徑 |
| `GENERATED_FILE_DIR` | | `./data/generated` | 產生檔案儲存路徑 |
| `MAX_FILE_SIZE_MB` | | `10` | 單檔上傳大小限制（MB） |
| `SESSION_EXPIRE_MINUTES` | | `480` | Session 過期時間（分鐘） |

### 支援的 AI Provider 範例

| Provider | `BASE_URL` | `MODEL` 範例 |
|----------|-----------|-------------|
| OpenRouter | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini`、`anthropic/claude-3.5-sonnet` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini`、`gpt-4o` |
| 自架 Ollama | `http://localhost:11434/v1` | `llama3`、`mistral` |

> 只要是 OpenAI-compatible 的 API 都可以使用。也可以在登入後台後從 UI 修改這些設定。

---

## 使用說明

### 學生操作流程

1. 打開 `http://localhost:8000`，進入學生登入頁
2. 輸入**暱稱**（用於識別你的歷史紀錄）和**共用密碼**
3. 進入主頁後：
   - **左側**：上傳課程資料（講義、筆記等，可選）
   - **右側**：上傳作業檔案、輸入作業敘述（必填，至少 10 字）
4. 選擇輸出格式（純文字 / Word / PDF / Excel）
5. 勾選學術誠信確認
6. 點「開始生成」
7. 查看即時進度 → 展開詳細過程 → 檢視結果
8. 複製文字或下載檔案
9. 可從右上角進入「歷史紀錄」查看過去的任務

### 管理者操作

1. 打開 `http://localhost:8000/admin/login`
2. 輸入管理者密碼
3. 可設定：
   - API Base URL / API Key / 模型名稱
   - Temperature / Max Tokens
   - 系統提示詞
   - 檔案大小限制
   - 啟用的輸出格式
4. 可測試 API 連線
5. 可查看設定變更紀錄

### 支援的檔案格式

| 格式 | 上傳 | 輸出 | 說明 |
|------|:----:|:----:|------|
| PDF | ✅ | ✅ | 擷取文字內容（純圖片 PDF 無法解析） |
| DOCX | ✅ | ✅ | 擷取段落與表格 |
| TXT | ✅ | ✅ | 純文字，自動偵測編碼 |
| MD | ✅ | - | Markdown 文件 |
| XLSX | ✅ | ✅ | 擷取工作表與欄位摘要 |
| CSV | ✅ | - | 自動偵測編碼，擷取表格 |

---

## API 端點一覽

| 端點 | 方法 | 說明 | 需登入 |
|------|------|------|:------:|
| `/api/health` | GET | 健康檢查 | - |
| `/api/auth/student/login` | POST | 學生登入 | - |
| `/api/auth/admin/login` | POST | 管理者登入 | - |
| `/api/auth/logout` | POST | 登出 | ✅ |
| `/api/auth/me` | GET | 取得目前使用者資訊 | ✅ |
| `/api/tasks` | POST | 建立 AI 任務 | ✅ |
| `/api/tasks/{id}` | GET | 取得任務詳情 | ✅ |
| `/api/tasks/{id}` | DELETE | 刪除任務 | ✅ |
| `/api/tasks/{id}/files` | POST | 上傳檔案至任務 | ✅ |
| `/api/tasks/{id}/events` | GET | SSE 即時進度串流 | ✅ |
| `/api/tasks/{id}/download/{file_id}` | GET | 下載產生的檔案 | ✅ |
| `/api/history` | GET | 歷史任務列表 | ✅ |
| `/api/admin/settings` | GET | 取得系統設定（API Key 遮罩）| Admin |
| `/api/admin/settings` | PUT | 更新系統設定 | Admin |
| `/api/admin/test-api` | POST | 測試 AI API 連線 | Admin |
| `/api/admin/settings/history` | GET | 設定變更紀錄 | Admin |

---

## 專案結構

```
niu-code-1142-project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口（API + 前端靜態檔案）
│   │   ├── config.py            # 環境變數設定
│   │   ├── database.py          # SQLAlchemy async 設定
│   │   ├── dependencies.py      # 認證依賴注入
│   │   ├── models/              # 資料庫模型
│   │   │   ├── user.py          # 使用者
│   │   │   ├── session.py       # Session
│   │   │   ├── task.py          # AI 任務
│   │   │   ├── uploaded_file.py # 上傳檔案
│   │   │   ├── progress_event.py# 進度事件
│   │   │   ├── generated_file.py# 產生的檔案
│   │   │   ├── system_setting.py# 系統設定
│   │   │   └── system_setting_history.py
│   │   ├── routers/             # API 路由
│   │   │   ├── auth.py          # 登入 / 登出
│   │   │   ├── tasks.py         # 任務 CRUD / 檔案上傳 / SSE / 下載
│   │   │   ├── history.py       # 歷史紀錄
│   │   │   └── admin.py         # 後台設定
│   │   ├── services/            # 商業邏輯
│   │   │   ├── auth_service.py  # 認證邏輯
│   │   │   ├── task_service.py  # 任務執行流程
│   │   │   ├── file_parser_service.py  # 檔案解析
│   │   │   ├── ai_service.py    # AI API 串接
│   │   │   ├── export_service.py# 文件輸出
│   │   │   └── progress_service.py    # 進度事件管理
│   │   └── utils/               # 工具函式
│   │       ├── security.py      # 密碼、遮罩
│   │       ├── validators.py    # 檔案 / 輸入驗證
│   │       └── file_utils.py    # 檔案路徑工具
│   ├── static/                  # 前端 build 產物（build.sh 產生）
│   ├── data/                    # 執行時資料（gitignore）
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                     # 實際環境變數（gitignore）
├── frontend/
│   ├── src/
│   │   ├── api/                 # Axios API 客戶端
│   │   ├── components/          # React 元件
│   │   ├── pages/               # 頁面元件
│   │   ├── types/               # TypeScript 型別
│   │   ├── App.tsx              # 路由設定
│   │   └── main.tsx             # 入口
│   ├── package.json
│   └── vite.config.ts           # Vite 設定（含 dev proxy）
├── Dockerfile                   # Multi-stage build（前端 + 後端）
├── docker-compose.yml           # 單一容器部署
├── build.sh                     # 本機 build 腳本
└── README.md
```

---

## 常見問題

### Q: Docker 啟動後打開網頁是空白的？

確認 `docker compose up --build` 有成功完成，查看 log：
```bash
docker compose logs -f
```

### Q: AI 生成失敗，顯示 401 Unauthorized？

`OPENAI_COMPATIBLE_API_KEY` 未設定或無效。請確認：
1. `backend/.env` 裡有填入正確的 API Key
2. 如果是 OpenRouter，到 [openrouter.ai/keys](https://openrouter.ai/keys) 確認 Key 有效
3. 也可以在後台設定頁修改 API Key 並點「測試 API 連線」

### Q: AI 生成失敗，顯示 timeout？

可能是模型回應太慢。可以在後台設定頁：
- 換一個更快的模型（例如 `openai/gpt-4o-mini`）
- 減少 Max Tokens

### Q: PDF 無法解析？

如果 PDF 是純圖片掃描檔，系統無法擷取文字。建議改用 DOCX 或 TXT 格式。

### Q: Docker 部署到公開網址？

在 `docker-compose.yml` 中修改 port mapping，搭配 Nginx Proxy Manager 或 Cloudflare Tunnel 反向代理即可：
```yaml
ports:
  - "8000:8000"   # 改成你需要的 port
```

### Q: 如何備份資料？

資料存在 Docker volume `app-data` 中，包含 SQLite 資料庫和上傳/產生的檔案：
```bash
docker compose cp app:/app/data ./backup
```

### Q: 如何重設資料庫？

```bash
docker compose down -v   # 刪除 volume
docker compose up --build -d
```

---

## 授權

本專案為期末專題作品，僅供學術展示與學習用途。
