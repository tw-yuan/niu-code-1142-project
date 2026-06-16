# LearnAI

多租戶 AI 學習輔助平台。後端使用 FastAPI、Celery、Redis、ChromaDB；前端使用 React、Vite、Tailwind CSS 與 Lucide icon。

## 已建立範圍

- JWT auth：註冊、登入、refresh、logout、me
- 文件上傳：PDF、Markdown、PPTX、DOCX
- 文件處理 pipeline：轉圖、Vision OCR、chunking、embedding、ChromaDB upsert
- WebSocket 文件狀態推播
- RAG 對話 SSE streaming
- 摘要、測驗、心智圖、閃卡 streaming API 基礎版
- Admin：使用者列表、統計、LLM config 更新
- 前端：登入、註冊、儀表板、文件管理、RAG 對話、Admin 基礎頁

## 啟動

```bash
cp .env.example .env
# 填入 SECRET_KEY 與 LLM_API_KEY
docker compose up -d --build
```

預設 compose 會啟動 production-safe 的 Nginx 前端。開發 hot reload 請明確套用 dev compose：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

服務對外使用 `http://localhost:8081`。前端預設使用相對路徑 `/api` 與 `/ws`，所以透過網域進入時不會打到瀏覽器端的 localhost。你的 reverse proxy 可指向：

```text
niu-1142-project.yuan-tw.net -> 151.246.244.22:8081
```

## 建立 Admin

第一個註冊帳號會自動成為 admin。也可以在 container 內執行：

```bash
docker compose exec backend python scripts/create_admin.py
```

## API

- 後端 API：`/api/*` 由前端 Nginx proxy 到 backend
- WebSocket：`/ws`
- Health check：`/api/health`
