# AI 課業輔助與作業草稿生成系統

一個以 **FastAPI + React + OpenAI-compatible tool calling** 實作的期末專題 Web 系統。
使用者上傳課程資料與作業需求後，後端啟動一個 **AI Agent**，由 Agent 自行透過一組受控
tools（讀檔 / 寫進度 / 寫 PDF/DOCX/XLSX / 結束）完成草稿生成，並產生可下載交付檔案。

> 本系統定位為學業輔助與草稿生成，**不會替使用者送交作業**，也**不協助規避 AI / 抄襲偵測**。

完整需求請見 [project.md](project.md)、Agent 規則與 tool 規格請見 [agents.md](agents.md)。

---

## 1. 系統架構

```
┌────────────────────────────────────────────────────────────┐
│                  Docker container (port 8000)               │
│  ┌─────────────────────┐    ┌────────────────────────────┐  │
│  │  FastAPI backend    │←───│  React/Vite SPA (built)    │  │
│  │  (uvicorn)          │    │  served as static files    │  │
│  │  • /api/*           │    └────────────────────────────┘  │
│  │  • Agent runtime    │                                    │
│  │  • Tool layer       │    Volume: ./data → /data          │
│  │  • SQLite DB        │      ├── uploads/{task_id}/        │
│  │                     │      ├── generated/{task_id}/      │
│  │                     │      └── db/app.db                  │
│  └─────────────────────┘                                    │
└────────────────────────────────────────────────────────────┘
                │
                ▼ tool_choice="auto"
        OpenRouter / OpenAI-compatible LLM
```

- **後端**：FastAPI、SQLAlchemy 2.x、SQLite、uv
- **前端**：React 18、Vite、TypeScript、Tailwind CSS
- **Agent loop**：`openai` Python SDK 對 OpenRouter 兼容端點打 chat.completions，
  循環呼叫 11 個 tools，由 tool 層落地副作用
- **進度推送**：Server-Sent Events（含 8 秒輪詢 fallback）
- **驗證**：HttpOnly cookie + itsdangerous 簽章

---

## 2. 快速啟動

### 2.1 先決條件
- Docker + docker compose
- OpenRouter（或其他 OpenAI-compatible）API Key

### 2.2 設定 `.env`

複製 `.env.example` 為 `.env`，填入 API Key：

```bash
cp .env.example .env
$EDITOR .env
```

最少需要設定：

| 變數 | 用途 |
|---|---|
| `APP_SECRET_KEY` | session cookie 簽章用，隨機字串 |
| `SHARED_LOGIN_PASSWORD` | 學生登入共用密碼 |
| `ADMIN_PASSWORD` | Admin 登入密碼 |
| `OPENAI_COMPATIBLE_API_KEY` | OpenRouter API Key（不會傳到前端） |
| `OPENAI_COMPATIBLE_MODEL` | 預設 `openai/gpt-5-mini` |

完整列表見 [.env.example](.env.example)。

### 2.3 起服務

```bash
docker compose up -d --build
```

服務會跑在 `:8000`，包含 API 與前端 SPA。可用反向代理（如 Nginx Proxy Manager）綁定 domain。

### 2.4 驗證

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

開啟瀏覽器：
- 學生：`http://localhost:8000/login`
- 管理者：`http://localhost:8000/admin/login`

---

## 3. 使用流程

### 3.1 學生（Student）

1. 進入 `/login`，輸入暱稱與共用密碼。同暱稱可承接歷史紀錄。
2. 進入主系統 `/app`：
   - 左側上傳課程資料（選填）：PDF、DOCX、TXT、MD、XLSX、CSV、圖片皆可。
   - 右側上傳作業檔案、輸入作業敘述。兩者至少擇一，作業敘述需 ≥ 10 字。
   - 勾選學術誠信確認 → 點「開始生成」。
3. 任務頁 `/tasks/{id}`：
   - **即時進度**：SSE 顯示 Agent 的每一步動作（讀檔、寫檔、log）。
   - **詳細處理過程**：展開可看 tool call timeline、引用、限制清單。
   - **Agent 結果**：講解可複製、每份產出檔案可下載。
4. 歷史紀錄 `/history`：可重看舊任務或刪除（連同檔案）。

### 3.2 管理者（Admin）

1. 進入 `/admin/login`，輸入管理者密碼。
2. `/admin/settings`：
   - API base URL、模型、temperature、max output tokens。
   - Agent loop 上限：`max_iterations`、單檔 MB、單任務檔案數。
   - 啟用 / 停用個別 tool（`finish` 永遠保留）。
   - 系統提示詞編輯（每次儲存留 SystemSettingHistory）。
   - 測試 API 連線（同時測 tool calling 支援度）。
3. `/history`：可看所有使用者任務摘要。
4. API Key 僅由環境變數注入，UI 只顯示遮罩（如 `sk-o…d7ef`）。

---

## 4. Demo 建議流程（依 `project.md` §12.2）

1. 開啟 `/login`，輸入暱稱與共用密碼。
2. 左側上傳一份 PDF 講義範例。
3. 右側上傳一份 DOCX/TXT 作業題目 + 輸入一段補充作業敘述。
4. 勾選學術誠信 → 開始生成。
5. 展示即時進度與 SSE 連線狀態。
6. 展開「詳細處理過程」顯示 tool call timeline。
7. 任務完成後展示 Agent 講解、複製按鈕、下載連結。
8. 進入歷史紀錄 → 找回剛剛任務。
9. 登出 → 進入 `/admin/login` 登入 Admin。
10. 進入 `/admin/settings`，展示 API 設定（API Key 已遮罩）、tool 啟停、系統提示詞、測試 API。

---

## 5. 後端架構

```
backend/
  app/
    main.py                 FastAPI app, router 註冊, SPA fallback
    config.py               pydantic-settings, 環境變數
    database.py             SQLAlchemy engine + Base + init_db
    deps.py                 get_current_session / require_admin

    models/                 全部 11 個 entity (project.md §7)
    routers/
      auth.py               學生 / Admin 登入、登出、/me
      tasks.py              建立任務、上傳檔案、取得詳情、run、刪除、agent-trace
      events.py             SSE 進度串流
      downloads.py          產出檔案下載（含 path-traversal 防護）
      history.py            /api/history (student=own, admin=all)
      admin.py              /api/admin/settings GET/PUT、test-api

    services/
      auth_service.py       密碼比對、session 建立 / 驗證
      task_service.py       任務 CRUD、上傳 + 解析 fan-out、刪除清理
      file_parser_service.py PDF/DOCX/TXT/MD/XLSX/CSV/image 解析
      progress_service.py   ProgressEvent CRUD + 跨執行緒 SSE 廣播
      system_setting_service.py 設定讀取 + 寫入 + history
      agent_runtime.py      Agent loop（OpenAI SDK + tool dispatch + 上限保護）

    tools/                  Agent tool 實作（agents.md §13）
      _helpers.py           ToolError、ToolContext、footer、truncate
      registry.py           OpenAI tool catalog + dispatch
      read_inputs.py        list_inputs / read_input_text / read_input_table
      annotate.py           log_progress / add_reference / add_limitation
      write_files.py        write_text/docx/pdf/xlsx_file（皆自動附加學術誠信 footer）
      finish.py             finish

    utils/
      security.py           cookie 簽章、密碼比對
      validators.py         nickname 驗證
      file_utils.py         sanitize_filename, detect_file_type, unique_storage_path
```

---

## 6. 安全 / 隱私守則（摘要）

- **API Key 永不外露**：只在後端讀環境變數，Admin UI 只看遮罩。
- **檔案沙箱**：上傳寫到 `/data/uploads/{task_id}/`、產出寫到 `/data/generated/{task_id}/`。
  - filename 經 `sanitize_filename` 去掉 `..`、`/`、`\`，僅保留 basename。
  - 下載端點 resolve 路徑後驗證仍在 `generated_file_dir` 下，否則 403。
- **權限**：每個 task / file 都用 `get_task_for_user` 檢查 ownership，跨使用者一律回 404。
- **Agent 安全**：強制 `max_iterations`，tool 連續同錯 5 次注入提醒，純文字回應 5 次後終止。
- **學術誠信**：tool 層自動附加 footer 到每份產出檔案，Agent 系統提示詞拒絕代繳交 / 規避偵測。
- **不執行使用者內容**：上傳檔案僅解析文字 / 表格，從不執行巨集或 eval Agent 提供的字串。

---

## 7. 開發者快速指令

```bash
# 重新 build + 重啟
docker compose build && docker compose up -d

# 看 log
docker compose logs -f app

# 進容器
docker compose exec app sh

# 跑單一 Python 腳本
docker compose exec app uv run python3 -c 'from app.config import get_settings; print(get_settings())'

# 砍掉資料庫 / 上傳 / 產出（!! 會清光所有任務）
rm -rf data/db/app.db data/uploads/* data/generated/*

# 看歷史 commit
git log --oneline
```

---

## 8. 已知限制

- 圖片格式（PNG/JPG/WEBP）僅保留 metadata，不做 OCR / vision 解析（Future Scope）。
- 單一 task 上限 8 份產出檔案（可由 Admin 調整）。
- 任務跑在同一個 worker process 的 BackgroundTasks 中，無 Celery / Redis 分散式佇列。
- 任務不會自動過期清理，須由使用者或 Admin 手動刪除。
- 前端尚未針對行動裝置調最佳化。
