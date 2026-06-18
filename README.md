# LearnAI

LearnAI 是一套多租戶 AI 學習輔助平台。使用者可以上傳課程文件，系統會透過 Vision LLM 做 OCR、切分文字、建立 ChromaDB 向量索引，之後提供 Streaming RAG 問答、摘要、測驗、心智圖、閃卡、筆記、課程管理與後台管理功能。

本專案以 Docker Compose 部署，後端主要使用 Python/FastAPI，前端使用 React/Vite/TypeScript。

## 文件導覽

- [PROJECT.md](./PROJECT.md)：完整專案說明，包含功能邏輯、技術棧、資料模型、AI 流程、API 模組、部署與維運重點。
- [SPEC.md](./SPEC.md)：產品規格與原始功能需求。
- [AGENTS.md](./AGENTS.md)：AI coding agent 開發規範與專案慣例。

## 目前功能

- 帳號系統：註冊、登入、JWT access token、refresh token、個人資料更新、密碼變更、帳號刪除與資料匯出流程。
- 文件管理：支援 PDF、Markdown、PPTX、DOCX，上傳後以 Celery 背景處理，透過 WebSocket 推播狀態。
- 文件處理 pipeline：檔案轉圖片、Vision OCR、OCR 快取、文字切分、Embedding、ChromaDB upsert。
- RAG 對話：支援文件範圍、課程文件範圍、空白對話快速提問建議、問題改寫、引用來源、SSE streaming 回答；個人文件範圍只列使用者自己上傳的文件，課程共享檔只在選擇課程範圍時出現；Socratic 模式不會把學生問題插入 system prompt；若使用者在既有對話旁改勾文件範圍，送出時會自動建立套用新範圍的對話；建立對話時會過濾已失效文件並用明確錯誤提示取代模糊 404。
- 學習工具：摘要、測驗生成與作答、心智圖、Anki 式正反面閃卡與間隔複習、錯題本、AI/生成內容保存筆記、學習目標；心智圖有獨立側欄入口並可直接選擇 ready 文件；測驗會正規化選項與答案，避免 A/B/C/D 與完整選項文字不一致造成誤判，並可一鍵顯示/隱藏全部答案；測驗、閃卡、筆記可切換個人文件或課程教材範圍，Chat/Quiz/Flashcards 可一鍵存成筆記，其中閃卡存筆記會防止同卡重複建立；測驗、心智圖、閃卡生成會以 Celery 背景任務保存進度，功能頁可點擊查看階段進度，離開頁面後仍會完成並回寫資料庫；Markdown 與心智圖節點文字支援 LaTeX/KaTeX 顯示。
- 課程功能：教師建立課程、加入碼、成員角色與批量管理、文件共享、全寬課程操作頁、教材批次加入與移除、教材版本/備註欄位、多選整課問答/測驗/閃卡、公告、可篩選/編輯/封存的作業、自訂作業提交內容、含聊天脈絡/留言/內部註記/結案摘要的求助 ticket、可單筆或批量編輯設定的課程測驗、可篩選/批量審核的預設核准題庫，以及可搜尋、排序、依風險篩選與查看單一學生明細的學習進度。
- Admin 後台：使用者、文件、對話、課程、LLM 設定、成本統計、可靠性事件、全站生成任務狀態、稽核紀錄、資料刪除管理。
- 角色化 UI：全站側欄依學習、課程、管理、帳號分區，文件列與管理員使用者列支援整列點擊，儀表板依學生、教師、管理者顯示常用入口與個人生成任務狀態。
- 法務與隱私：上傳前著作權同意、使用者資料匯出、刪除排程與強制清除。

## 技術棧

| 區域 | 技術 |
|------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy async, Pydantic Settings |
| Worker | Celery, Redis |
| AI / LLM | OpenAI-compatible API, Chat Streaming, Vision OCR, Embeddings |
| Vector DB | ChromaDB persistent client |
| Database | SQLite 預設，可透過 `DATABASE_URL` 切換 SQLAlchemy 支援的資料庫 |
| Frontend | React 18, Vite 5, TypeScript, Tailwind CSS v4, Zustand, Lucide, Recharts |
| Deploy | Docker Compose, Nginx frontend reverse proxy |

## 啟動

先建立環境變數檔：

```bash
cp .env.example .env
```

至少需要填入：

```env
SECRET_KEY=
LLM_API_KEY=
```

`LLM_API_KEY` 與 `LLM_BASE_URL` 是三種 LLM 功能的共用 fallback。若要分開控成本，可另外設定 `LLM_CHAT_API_KEY` / `LLM_CHAT_BASE_URL`、`LLM_VISION_API_KEY` / `LLM_VISION_BASE_URL`、`LLM_EMBED_API_KEY` / `LLM_EMBED_BASE_URL`。

如果 Admin 後台已存過 LLM 設定，DB 會覆蓋 `.env`。可在 Admin 的 LLM / Fallback 設定中按「重設為 .env 預設值」清除 DB override。

Rate limit 可用 `.env` 調整：`GLOBAL_RATE_LIMIT_PER_MINUTE` 控制全域 API 每分鐘上限；登入另以 `LOGIN_RATE_LIMIT_PER_IDENTIFIER`、`LOGIN_RATE_LIMIT_PER_IP`、`LOGIN_RATE_LIMIT_WINDOW_SECONDS` 控制，避免同一代理出口 IP 下的不同使用者互相擋登入。

啟動 production-style compose：

```bash
docker compose up -d --build
```

啟動開發 hot reload compose：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

預設入口：

- Web UI: `http://localhost:8081`
- Backend API health: `http://localhost:8081/api/health`
- Backend dev port: `http://localhost:8000`，僅在套用 `docker-compose.dev.yml` 時暴露
- WebSocket: `/ws`

## 常用指令

```bash
# 查看服務狀態
docker compose ps

# 查看後端與 worker log
docker compose logs -f backend worker

# 重啟後端
docker compose restart backend

# 建立或更新 admin 帳號
docker compose exec backend python scripts/create_admin.py

# 後端測試
docker compose exec backend pytest

# 前端型別檢查
docker compose exec frontend npm run lint
```

第一個註冊帳號會自動成為 admin，也可以使用 `scripts/create_admin.py` 在 container 內建立。

## 核心規則

- Streaming first：所有主要 LLM 回應透過 SSE streaming 回傳。
- 多租戶隔離：資料庫、ChromaDB 與本地檔案存取都必須限制在使用者可存取範圍內。
- LLM 統一入口：Chat、Vision、Embedding 必須透過 `backend/app/services/llm_client.py`。
- Docker first：本地測試與部署優先使用 Docker Compose，避免在主機上長時間佔用不必要 port。
