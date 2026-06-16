# LearnAI 專案完整說明

> 本文件用來讓沒有閱讀程式碼的人理解 LearnAI 的完整專案內容、系統邏輯、技術棧、資料流與部署方式。  
> 最後整理日期：2026-06-16

## 快速索引

- 想先理解產品目標：看第 1 到 3 節。
- 想理解部署與服務關係：看第 4、5、21 節。
- 想理解後端如何分層：看第 6、14、15 節。
- 想理解文件上傳後發生什麼事：看第 8 節。
- 想理解 RAG 與 citation：看第 9 節。
- 想理解摘要、測驗、心智圖、閃卡等 AI 功能：看第 10 節。
- 想理解課程、教師、學生功能：看第 11 節。
- 想理解 Admin、成本、隱私、稽核：看第 12、13、18 節。
- 想接手開發或維運：看第 16 到 25 節。

## 1. 專案定位

LearnAI 是一套多租戶 AI 學習輔助平台。核心情境是學生或教師把課程資料上傳到平台，系統自動完成文字擷取、向量化與索引，之後使用者可以用 AI 做問答、摘要、測驗、心智圖、閃卡與筆記管理。教師可以建立課程、共享文件、發布測驗與作業，管理員可以管理使用者、文件、課程、LLM 設定、成本與稽核紀錄。

本專案的展示重點不是單一 AI chat，而是完整的「文件進入系統後如何變成可互動學習素材」流程：

1. 使用者上傳 PDF、Markdown、PPTX 或 DOCX。
2. 背景 worker 將文件轉成文字。
3. 系統切分文字並建立 embedding。
4. ChromaDB 保存 chunk 向量與頁碼、文件、使用者等 metadata。
5. 使用者透過 RAG 問答或學習工具取用這些資料。
6. LLM 回應以 SSE streaming 逐步回傳，前端即時呈現。
7. 使用紀錄、token 成本、測驗成績、閃卡複習與課程進度會回寫資料庫。

## 2. 核心設計原則

### 2.1 Streaming first

所有主要 LLM 生成型功能都採用 Server-Sent Events streaming，不等待完整內容產生後才回傳。這包含：

- RAG 問答
- 摘要生成
- 測驗 JSON 生成
- 心智圖 JSON 或 Markdown 生成
- 心智圖節點延伸
- 閃卡 JSON 生成

後端回傳格式固定以 `data: ...\n\n` 組成，最後送出 `data: [DONE]`。前端用 `frontend/src/lib/stream.ts` 的 `streamFetch()` 統一消費。

### 2.2 多租戶隔離

平台資料必須依使用者隔離。主要隔離方式如下：

- 關聯資料庫：查詢使用者資料時必須帶 `user_id` 或透過課程成員權限判斷。
- ChromaDB：查詢向量時預設 `where={"user_id": {"$eq": user_id}}`，課程共享文件才會額外允許 shared doc ids。
- 本地檔案：上傳文件放在 `data/uploads/{user_id}/{doc_id}/`，並透過 `safe_join()` 避免 path traversal。
- 課程文件：不是文件擁有者時，必須是課程成員且文件被加入課程才可讀取。

### 2.3 LLM 統一入口

所有 Chat、Streaming Chat、Vision OCR、Embedding 都必須透過 `backend/app/services/llm_client.py` 的 `LLMClient`。這個設計把以下能力集中在同一層：

- OpenAI-compatible provider 呼叫
- model/base URL/API key 設定
- fallback provider
- retry
- token usage 記錄
- 成本估算
- token quota 檢查
- 系統事件記錄

## 3. 技術棧

| 區域 | 技術 | 用途 |
|------|------|------|
| 後端語言 | Python 3.12 | 主要後端與 worker 邏輯 |
| API framework | FastAPI | REST API、SSE、WebSocket |
| ORM | SQLAlchemy 2.0 async | 資料庫模型與查詢 |
| 設定 | Pydantic Settings | `.env` 環境變數載入 |
| 關聯資料庫 | SQLite 預設 | `data/db/learnai.db`，也可透過 `DATABASE_URL` 切換 |
| 向量資料庫 | ChromaDB PersistentClient | 文件 chunk embedding 檢索 |
| 背景任務 | Celery | 文件處理與維護任務 |
| Broker/backend | Redis 7 | Celery broker/result backend、WebSocket pub/sub |
| LLM SDK | OpenAI Python SDK | OpenAI-compatible Chat/Vision/Embedding |
| 文件轉換 | PyMuPDF、LibreOffice headless | PDF/PPTX/DOCX 轉頁面圖片 |
| 前端 | React 18、Vite 5、TypeScript | SPA 使用者介面 |
| UI | Tailwind CSS v4、Lucide icons、Recharts | 樣式、icon、圖表 |
| 狀態管理 | Zustand | auth store |
| 部署 | Docker Compose、Nginx | backend、worker、beat、redis、frontend |

## 4. 執行架構

Docker Compose 啟動的服務：

| Service | 職責 |
|---------|------|
| `frontend` | Nginx serve Vite build；proxy `/api/` 到 backend，proxy `/ws` 到 backend WebSocket |
| `backend` | FastAPI API server，提供 REST、SSE、WebSocket、health check |
| `worker` | Celery worker，處理文件轉換、OCR、embedding、ChromaDB upsert |
| `beat` | Celery beat，定期推播 quota warning 與清除到期刪除帳號 |
| `redis` | Celery broker/result backend、WebSocket pub/sub |

Production-style compose 只對外暴露前端 Nginx：

- Web UI：`http://localhost:8081`
- API：由 Nginx 的 `/api/` proxy 到 backend container 的 `:8000`
- WebSocket：由 Nginx 的 `/ws` proxy 到 backend container 的 `/ws`

開發 compose 額外暴露 backend port `8000`，並用 frontend dev server 支援 hot reload。

## 5. 目錄結構

```text
.
├── README.md
├── PROJECT.md
├── SPEC.md
├── AGENTS.md
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── routers/
│   │   ├── services/
│   │   ├── tasks/
│   │   ├── models/
│   │   └── prompts/
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── nginx/default.conf
│   ├── package.json
│   └── src/
└── scripts/
    └── create_admin.py
```

執行時資料放在 `data/`，不應提交到 git：

```text
data/
├── uploads/{user_id}/{doc_id}/
│   ├── original.pdf
│   └── pages/
│       ├── page_001.png
│       └── ocr_cache.json
├── chroma/
├── db/learnai.db
└── exports/{user_id}/learnai-export.zip
```

## 6. 後端架構

### 6.1 FastAPI 入口

`backend/app/main.py` 建立 FastAPI app，掛載下列 router：

- `auth`
- `documents`
- `chat`
- `summary`
- `quiz`
- `mindmap`
- `flashcards`
- `notes`
- `goals`
- `courses`
- `legal`
- `admin`

它也提供：

- CORS middleware
- 全域 rate limit middleware，每 IP 每 60 秒 120 requests
- DB startup 初始化
- health check
- WebSocket `/ws`

### 6.2 Router 與 Service 分工

Router 層只處理 HTTP request/response、依賴注入與 SSE 包裝。實際業務邏輯集中在 service：

| Service | 職責 |
|---------|------|
| `AuthService` | 註冊、登入、profile 更新、密碼變更 |
| `DocumentService` | 上傳、列表、刪除、封存、還原、內容讀取、coverage |
| `RAGService` | 對話 session、RAG 檢索、prompt 組裝、stream answer、引用紀錄 |
| `LearningService` | 摘要、測驗、閃卡、學習 artifact |
| `MindmapTreeService` | tree JSON 心智圖、節點延伸、格式正規化 |
| `CoursesService` | 課程、成員、文件共享、公告、作業、help request、進度 |
| `AdminService` | 使用者、文件、對話、課程、config、統計與稽核管理 |
| `PrivacyService` | 資料匯出、刪除申請、確認刪除、強制清除 |
| `LegalService` | 著作權等同意紀錄 |
| `LLMClient` | Chat/Vision/Embedding 統一入口 |
| `ChromaService` | ChromaDB upsert/query/delete |

## 7. 認證與權限

### 7.1 使用者角色

系統使用 `users.role` 區分角色：

- `student`：一般學生，能上傳自己的文件、使用 AI 學習工具、加入課程。
- `teacher`：可以建立課程；在自己課程內通常是 instructor。
- `admin`：可以進入後台，管理使用者、文件、課程、LLM 設定與資料刪除。

課程內另有 `course_members.role`：

- `student`
- `ta`
- `instructor`

課程權限不完全等同於平台角色。例如 teacher 建立課程後，會成為該課程的 instructor。

### 7.2 JWT 與 Refresh Token

登入成功後：

- API response 回傳 access token。
- refresh token 放入 httpOnly cookie。
- access token 預設 15 分鐘。
- refresh token 預設 7 天。

前端 `apiFetch()` 遇到 401 時會自動呼叫 `/auth/refresh`，成功後重試原請求。

### 7.3 第一個帳號自動成為 admin

`AuthService.register()` 會檢查 users 數量。第一個註冊帳號 role 設為 `admin`，之後預設為 `student`。也可以使用 `docker compose exec backend python scripts/create_admin.py` 建立 admin。

## 8. 文件處理流程

### 8.1 支援格式

| 格式 | 處理方式 |
|------|----------|
| PDF | PyMuPDF 依頁轉 PNG，再送 Vision OCR |
| PPTX | LibreOffice headless 轉 PDF，再用 PyMuPDF 轉 PNG |
| DOCX | LibreOffice headless 轉 PDF，再用 PyMuPDF 轉 PNG |
| Markdown | 直接讀文字，不需要 Vision OCR |

檔案上限由 `MAX_UPLOAD_SIZE_MB` 控制，預設 50 MB。PDF/Office 頁數上限由 `MAX_PAGES_PER_DOC` 控制，預設 100 頁。

### 8.2 上傳階段

使用者呼叫：

- `POST /documents/upload`
- `POST /documents/upload/batch`

流程：

1. Router 先確認使用者已登入。
2. 上傳前必須有法務同意紀錄，例如著作權聲明。
3. `DocumentService.upload()` 建立 `Document` DB row，初始狀態為 `uploading`。
4. `storage.save_upload()` 檢查副檔名、MIME type、大小限制，並寫入 `data/uploads/{user_id}/{doc_id}/original.{ext}`。
5. `storage.ensure_user_quota()` 檢查使用者儲存空間配額。
6. 送出 Celery task：`process_document.apply_async(args=[doc.id, user_id])`。

同一使用者處理中的文件數量若達 10 份，會回傳 429。

### 8.3 Celery 文件處理階段

Celery task：`backend/app/tasks/document_tasks.py::process_document`

狀態機：

```text
uploading
  -> converting
  -> ocr_processing
  -> embedding
  -> ready
  -> error
```

PDF/PPTX/DOCX：

1. 狀態改為 `converting`，透過 WebSocket 推播。
2. `converter.convert_to_images()` 產生 `pages/page_001.png` 等圖片。
3. 狀態改為 `ocr_processing`。
4. `ocr_service.ocr_document()` 逐頁把 PNG base64 傳給 Vision LLM。
5. 每頁 OCR 結果寫入 `pages/ocr_cache.json`。
6. 每完成一頁透過 WebSocket 推播 progress。
7. 狀態改為 `embedding`。
8. `chunker.chunk_text()` 依頁碼 marker 與句子邊界切 chunk。
9. `LLMClient.embed()` 批次建立 embedding。
10. `ChromaService.upsert_chunks()` 寫入 ChromaDB。
11. DB 更新 `status=ready`、`page_count`、`chunk_count`。
12. WebSocket 推播 `doc_ready`。

Markdown：

1. 直接讀取原始文字。
2. 包成 `=== 第 1 頁 ===`。
3. 進入 chunk、embedding、upsert 流程。

### 8.4 OCR 快取

OCR 結果存在：

```text
data/uploads/{user_id}/{doc_id}/pages/ocr_cache.json
```

格式大致如下：

```json
{
  "1": {
    "text": "...",
    "model": "vision",
    "cached_at": "..."
  }
}
```

重新處理同一份文件時，如果頁碼已在 cache 中，就不再呼叫 Vision LLM。

### 8.5 Chunking

`chunker.chunk_text()` 預設：

- chunk size：512 字元
- overlap：64 字元
- 先解析 `=== 第 N 頁 ===`
- 再以中文與英文標點、換行作為句子切分點
- 每個 chunk 保存：
  - `text`
  - `page_num`
  - `chunk_index`

### 8.6 ChromaDB 寫入

Chroma collection 名稱是 `documents`，距離空間為 cosine。每個 chunk 寫入：

- id：`{doc_id}__chunk_{chunk_index}`
- embedding
- document text
- metadata：
  - `user_id`
  - `doc_id`
  - `filename`
  - `page_num`
  - `chunk_index`

ChromaDB 寫入與刪除使用 `filelock` 保護，降低 FastAPI 與 Celery worker 共用 persistent path 時的並發風險。

## 9. RAG 對話流程

### 9.1 對話 session

使用者先建立 chat session：

```http
POST /chat/sessions
```

可指定：

- `title`
- `doc_ids`
- `course_id`
- `mode`

`mode` 可為：

- `enhanced`：一般增強問答，使用 `rag_chat.yaml`
- `strict`：嚴格根據文件回答，使用 `rag_strict.yaml`
- `socratic`：蘇格拉底式引導，使用 `rag_socratic.yaml`

### 9.2 Streaming answer

使用者送出訊息：

```http
POST /chat/sessions/{session_id}/message
```

流程：

1. 依 `session_id` 與 `user_id` 取得 session。
2. 取最近對話歷史。
3. 如果有歷史，先用 `LLMClient.chat()` 做 query rewriting，將追問改寫成可檢索的獨立查詢。
4. 用 rewritten question 呼叫 `LLMClient.embed()` 取得查詢向量。
5. 根據 session 的文件範圍與課程共享文件決定檢索範圍。
6. `ChromaService.query_chunks()` 查詢最相關 chunk。
7. 組成 context 與 citations。
8. 建立 `RAGRun` 與 `RAGRetrievedChunk` 追蹤此次檢索。
9. 依模式載入 prompt。
10. `LLMClient.stream_chat()` streaming 回答。
11. Router 每收到一段 chunk，就送出 SSE：

```text
data: {"type":"chunk","content":"..."}
```

12. 回答完成後計算 citation support 狀態與 latency。
13. 送出 citations event。
14. 儲存 user message 與 assistant message。
15. 送出 `[DONE]`。

### 9.3 Citation

每筆 citation 包含：

- `index`
- `doc_id`
- `filename`
- `page`
- `chunk_index`
- `scope`：`personal` 或 `course`
- `distance`
- `snippet`
- `retrieval_score`
- `support_status`

`support_status` 會在回答完成後用簡易文字比對標記為：

- `supported`
- `partial`
- `unverified`

此標記不是正式 fact-check，只是用來輔助觀察答案與檢索片段的對應程度。

## 10. 其他 AI 學習工具

### 10.1 摘要

端點：

- `POST /summary/stream`
- `GET /summary/{doc_id}`

支援：

- `full`
- `bullets`

流程：

1. 取得可存取文件。
2. 讀取該文件所有 chunks 組成 context。
3. 載入 `summary_full.yaml` 或 `summary_bullets.yaml`。
4. 用 `LLMClient.stream_chat()` 回傳摘要 chunk。
5. 完成後把結果存為 `LearningArtifact(kind="summary")`。
6. SSE 送出 `summary_meta`，包含 `summary_id`。

### 10.2 測驗

端點：

- `POST /quiz/stream`
- `GET /quiz`
- `GET /quiz/{quiz_id}`
- `POST /quiz/{quiz_id}/attempt`
- `GET /quiz/{quiz_id}/attempts`
- `GET /quiz/wrongbook`
- `POST /quiz/{quiz_id}/publish/{course_id}`

生成流程：

1. 驗證文件可存取。
2. 如果指定課程發布，使用者必須是 instructor 或 ta，且文件必須屬於該課程共享文件。
3. 組 context。
4. 載入 `quiz_generate.yaml`。
5. 以 `response_format={"type": "json_object"}` 要求 LLM 產生 JSON。
6. 前端 streaming 收 chunk，後端串流結束後解析 JSON。
7. 建立 `Quiz` row。
8. 若 `publish_to_course=true`，同時建立 `CourseQuiz` row。
9. SSE 送出 `quiz_meta`，包含 quiz id 與題數。

作答流程：

1. 取得 quiz。
2. 若是 course quiz，檢查可用時間、作答次數限制與答案可見時間。
3. 依題目答案計分。
4. 建立 `QuizAttempt`。
5. 回傳分數與 diagnostics。

錯題本會從使用者作答紀錄整理錯題，閃卡功能也能用錯題生成複習卡。

### 10.3 心智圖

端點：

- `POST /mindmap/stream`
- `GET /mindmap/{doc_id}`
- `POST /mindmap/{artifact_id}/nodes/{node_id}/expand/stream`
- `PUT /mindmap/{artifact_id}`

目前主要支援 tree JSON 格式：

- schema version：2
- 初始深度上限：4
- 延伸深度上限：5
- 每次延伸最多子節點：6
- 總節點預設上限：80

流程：

1. 取得文件 context。
2. 載入 `mindmap_tree.yaml`。
3. 用 JSON response streaming 產生 tree。
4. `normalize_mindmap_tree()` 清理 title、id、depth、children、source refs 等欄位。
5. 存成 `LearningArtifact(kind="mindmap_tree")`。
6. 前端用 `MindmapCanvas` 呈現。
7. 使用者展開節點時，系統用節點 path 做 focused retrieval，再要求 LLM 只產生該節點子節點。
8. 後端把新 children append 到原 tree，並用 `mindmap_patch` event 回傳。

### 10.4 閃卡

端點：

- `POST /flashcards/stream`
- `GET /flashcards`
- `POST /flashcards`
- `POST /flashcards/from-wrongbook`
- `PUT /flashcards/{card_id}`
- `DELETE /flashcards/{card_id}`
- `POST /flashcards/{card_id}/review`

功能：

- 從文件自動生成 front/back JSON。
- 可手動建立與編輯。
- 可從錯題本建立。
- 使用 `quality` 0 到 5 記錄複習品質。
- 保存 repetition、ease factor、interval days、next review。

### 10.5 筆記

端點：

- `POST /notes`
- `GET /notes`
- `PUT /notes/{note_id}`
- `DELETE /notes/{note_id}`
- `GET /notes/export/{doc_id}`

筆記可關聯：

- 文件
- 對話 session
- 來源頁碼
- 來源類型：`chat`、`summary`、`manual`

### 10.6 學習目標

端點：

- `POST /goals`
- `GET /goals`
- `GET /goals/today`
- `PUT /goals/{goal_id}`
- `DELETE /goals/{goal_id}`

學習目標關聯文件，包含 title、target date、focus hint 與 status。Dashboard 會讀取今日任務。

### 10.7 文件 coverage

端點：

```http
GET /documents/{doc_id}/coverage
```

此功能把文件頁面切成每 10 頁一個區段，彙整：

- quiz attempts
- quiz score average
- flashcard count
- mastered flashcards
- chat mentions
- coverage score

`coverage_score` 是加權估算：

- quiz score average：40%
- flashcard mastered ratio：40%
- chat mentions：20%，最多採計 3 次

## 11. 課程功能

課程模組讓 teacher/admin 可以建立課程，學生透過加入碼加入。課程可共享文件、發布測驗、建立公告與作業，並追蹤學生進度。

### 11.1 課程與加入碼

端點：

- `POST /courses`
- `GET /courses`
- `GET /courses/{course_id}`
- `PUT /courses/{course_id}`
- `POST /courses/{course_id}/join-code/reset`
- `DELETE /courses/{course_id}`
- `POST /courses/join`
- `POST /courses/{course_id}/leave`

建立課程需要平台角色為 `teacher` 或 `admin`。建立者會成為該課程 `instructor`。

### 11.2 成員管理

端點：

- `GET /courses/{course_id}/members`
- `PUT /courses/{course_id}/members/{member_user_id}`
- `DELETE /courses/{course_id}/members/{member_user_id}`

課程成員角色：

- `student`
- `ta`
- `instructor`

權限大致如下：

- owner 不可被移除，也不可離開自己的課程。
- instructor 可管理多數課程設定與成員。
- ta 可協助管理學生與課程資源，但某些 owner/instructor 操作受限。

### 11.3 課程文件共享

端點：

- `POST /courses/{course_id}/documents`
- `DELETE /courses/{course_id}/documents/{doc_id}`

只有 ready 狀態且由操作者擁有的文件可以加入課程。加入後課程成員可以在 RAG、摘要、心智圖等功能中讀取該文件。移除文件時使用 soft remove：

- `is_active=0`
- `removed_at`
- `removed_by`

文件擁有者封存文件時，也會把對應的 course document 標成 inactive。

### 11.4 公告

端點：

- `GET /courses/{course_id}/announcements`
- `POST /courses/{course_id}/announcements`
- `PUT /courses/{course_id}/announcements/{announcement_id}`
- `DELETE /courses/{course_id}/announcements/{announcement_id}`
- `POST /courses/{course_id}/announcements/{announcement_id}/read`

建立公告後可透過 WebSocket 推播 `course_announcement`。

### 11.5 Help request

端點：

- `GET /courses/{course_id}/help-requests`
- `POST /courses/{course_id}/help-requests`
- `PUT /courses/{course_id}/help-requests/{request_id}`

學生可以建立 help request，也可以從 ChatPage 針對對話內容建立求助。教師/TA 可以更新狀態、優先級、指派對象等。

### 11.6 作業

端點：

- `GET /courses/{course_id}/assignments`
- `POST /courses/{course_id}/assignments`
- `PUT /courses/{course_id}/assignments/{assignment_id}`
- `DELETE /courses/{course_id}/assignments/{assignment_id}`
- `POST /courses/{course_id}/assignments/{assignment_id}/submit`

作業可關聯文件或測驗，種類包含：

- `custom`
- `quiz`
- `read_summary`
- `note`
- `flashcards`

提交紀錄存在 `course_assignment_submissions`。

### 11.7 課程進度

端點：

- `GET /courses/dashboard`
- `GET /courses/{course_id}/progress`
- `GET /courses/{course_id}/quizzes`

課程進度會彙整學生：

- chat sessions
- chat messages
- notes
- flashcards
- due flashcards
- mastered flashcards
- quizzes
- assigned quizzes
- quiz attempts
- quiz average score
- last activity
- risk level

教師/TA 可以用這些資訊了解學生學習狀態。

## 12. Admin 後台

Admin 入口在前端 `/admin`。後端所有 admin API 都需要平台角色 `admin`。

### 12.1 使用者管理

端點：

- `GET /admin/users`
- `POST /admin/users`
- `GET /admin/users/{user_id}`
- `PUT /admin/users/{user_id}`
- `POST /admin/users/{user_id}/reset-password`
- `GET /admin/users/{user_id}/usage`

可管理：

- username
- email
- role
- active status
- storage quota
- token quota
- 密碼重設

系統避免管理員停用或降級自己的 admin 帳號，也避免最後一個 active admin 被移除。

### 12.2 文件、對話、課程管理

端點：

- `GET /admin/documents`
- `DELETE /admin/documents/{doc_id}`
- `GET /admin/chat-sessions`
- `GET /admin/chat-sessions/{session_id}`
- `DELETE /admin/chat-sessions/{session_id}`
- `GET /admin/courses`
- `GET /admin/courses/{course_id}`
- `PUT /admin/courses/{course_id}`
- `DELETE /admin/courses/{course_id}`
- `PUT /admin/courses/{course_id}/members`
- `DELETE /admin/courses/{course_id}/members/{user_id}`
- `POST /admin/courses/{course_id}/documents`
- `DELETE /admin/courses/{course_id}/documents/{doc_id}`

Admin 刪除文件時會同步：

- 刪 DB document row
- 刪 Chroma chunks
- 刪本地 upload directory
- 寫入 audit log

### 12.3 LLM 設定

端點：

- `GET /admin/config`
- `PUT /admin/config`

設定存於 `admin_config` 的 `llm_config` key。可覆蓋：

- chat provider
- vision provider
- embedding provider
- cost per 1k tokens
- fallback providers

若 DB 沒有設定，會使用 `.env` 中的：

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_CHAT_MODEL`
- `LLM_VISION_MODEL`
- `LLM_EMBED_MODEL`

### 12.4 成本、可靠性與稽核

端點：

- `GET /admin/stats`
- `GET /admin/stats/cost`
- `GET /admin/stats/reliability`
- `GET /admin/audit-logs`

成本統計基於 `token_usage`：

- input tokens
- output tokens
- image count
- model
- provider
- price snapshot
- cost USD

可靠性事件基於 `system_events`，例如 LLM fallback 發生時會記錄。

Audit log 記錄管理操作、資料匯出、刪除申請、強制清除等事件。

### 12.5 刪除與隱私管理

端點：

- `GET /admin/deletions`
- `GET /admin/users/{user_id}/deletion-status`
- `POST /admin/users/{user_id}/force-purge`

Admin 可以檢視資料刪除排程，或強制清除某使用者資料。

## 13. 法務與隱私

### 13.1 上傳前同意

使用者上傳文件前，需要先對指定 consent type 建立同意紀錄。相關端點：

- `GET /legal/consents`
- `POST /legal/consent`

同意紀錄保存：

- user id
- consent type
- consented at
- IP address

### 13.2 使用者資料匯出

端點：

- `POST /auth/me/export-request`
- `GET /auth/me/export-download`

匯出流程：

1. 產生 `data/exports/{user_id}/learnai-export.zip`。
2. zip 內包含 profile、documents metadata、chat history、flashcards、quizzes、quiz attempts、notes。
3. 匯出連結有效 24 小時。
4. 下載時檢查 export path 與 expiry。

### 13.3 使用者刪除流程

端點：

- `POST /auth/me/delete-request`
- `POST /auth/me/delete-confirm`
- `POST /auth/me/delete-cancel`

流程：

1. 使用者要求刪除時，系統產生 6 位確認碼。
2. 設定 `deletion_scheduled_at = now + 30 days`。
3. 使用者用確認碼確認後，帳號設為 inactive。
4. Celery beat 每日執行 `purge_due_users` 清除到期帳號。
5. Admin 可提早 force purge。

強制清除會刪除：

- 使用者 Chroma chunks
- upload directory
- export directory
- 使用者擁有的課程
- users row，並依外鍵 cascade 清除相關資料

## 14. 資料模型

主要資料表如下：

| Table | 用途 |
|-------|------|
| `users` | 帳號、角色、配額、刪除與匯出狀態 |
| `documents` | 上傳文件 metadata、處理狀態、頁數、chunk 數 |
| `chat_sessions` | RAG 對話 session、文件範圍、課程範圍、模式 |
| `chat_messages` | 對話訊息、citations、token count |
| `quizzes` | 測驗設定與題目 JSON |
| `quiz_attempts` | 使用者作答紀錄、分數、耗時 |
| `course_quizzes` | 測驗發布到課程的設定 |
| `course_assignments` | 課程作業 |
| `course_assignment_submissions` | 作業提交紀錄 |
| `course_announcements` | 課程公告 |
| `course_announcement_reads` | 公告已讀狀態 |
| `course_help_requests` | 課程求助請求 |
| `learning_artifacts` | 摘要、心智圖等 AI 生成學習產物 |
| `flashcards` | 閃卡與間隔複習狀態 |
| `notes` | 使用者筆記 |
| `learning_goals` | 學習目標 |
| `token_usage` | LLM 使用量與成本 |
| `rag_runs` | 每次 RAG 執行紀錄 |
| `rag_retrieved_chunks` | RAG 檢索到的 chunk 與 citation 支援狀態 |
| `admin_config` | LLM config、成本 config、fallback provider |
| `system_events` | 系統事件，例如 fallback |
| `audit_logs` | 管理與隱私相關操作紀錄 |
| `courses` | 課程 |
| `course_members` | 課程成員與角色 |
| `course_documents` | 課程共享文件 |
| `legal_consents` | 使用者法務同意紀錄 |

所有主鍵使用字串 UUID，方便相容 SQLite 與其他 SQL database。

## 15. API 模組總覽

### 15.1 Auth

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
PUT  /auth/me
PUT  /auth/me/password
POST /auth/me/delete-request
POST /auth/me/delete-confirm
POST /auth/me/delete-cancel
POST /auth/me/export-request
GET  /auth/me/export-download
```

### 15.2 Documents

```text
POST   /documents/upload
POST   /documents/upload/batch
GET    /documents
GET    /documents/{doc_id}
DELETE /documents/{doc_id}
POST   /documents/{doc_id}/archive
POST   /documents/{doc_id}/restore
GET    /documents/{doc_id}/status
GET    /documents/{doc_id}/coverage
GET    /documents/{doc_id}/content
GET    /documents/{doc_id}/pages/{page_num}
```

### 15.3 Chat

```text
POST   /chat/sessions
GET    /chat/sessions
GET    /chat/sessions/{session_id}
DELETE /chat/sessions/{session_id}
POST   /chat/sessions/{session_id}/message
```

### 15.4 Learning Tools

```text
POST /summary/stream
GET  /summary/{doc_id}

POST /quiz/stream
GET  /quiz
GET  /quiz/wrongbook
POST /quiz/{quiz_id}/publish/{course_id}
GET  /quiz/{quiz_id}
POST /quiz/{quiz_id}/attempt
GET  /quiz/{quiz_id}/attempts

POST /mindmap/stream
GET  /mindmap/{doc_id}
POST /mindmap/{artifact_id}/nodes/{node_id}/expand/stream
PUT  /mindmap/{artifact_id}

POST   /flashcards/stream
GET    /flashcards
POST   /flashcards
POST   /flashcards/from-wrongbook
PUT    /flashcards/{card_id}
DELETE /flashcards/{card_id}
POST   /flashcards/{card_id}/review

POST   /notes
GET    /notes
PUT    /notes/{note_id}
DELETE /notes/{note_id}
GET    /notes/export/{doc_id}

POST   /goals
GET    /goals
GET    /goals/today
PUT    /goals/{goal_id}
DELETE /goals/{goal_id}
```

### 15.5 Courses

```text
POST   /courses
GET    /courses
POST   /courses/join
GET    /courses/dashboard
GET    /courses/{course_id}
PUT    /courses/{course_id}
POST   /courses/{course_id}/join-code/reset
DELETE /courses/{course_id}
GET    /courses/{course_id}/members
PUT    /courses/{course_id}/members/{member_user_id}
DELETE /courses/{course_id}/members/{member_user_id}
POST   /courses/{course_id}/leave
GET    /courses/{course_id}/progress
GET    /courses/{course_id}/quizzes
GET    /courses/{course_id}/announcements
POST   /courses/{course_id}/announcements
PUT    /courses/{course_id}/announcements/{announcement_id}
DELETE /courses/{course_id}/announcements/{announcement_id}
POST   /courses/{course_id}/announcements/{announcement_id}/read
GET    /courses/{course_id}/help-requests
POST   /courses/{course_id}/help-requests
PUT    /courses/{course_id}/help-requests/{request_id}
GET    /courses/{course_id}/assignments
POST   /courses/{course_id}/assignments
PUT    /courses/{course_id}/assignments/{assignment_id}
DELETE /courses/{course_id}/assignments/{assignment_id}
POST   /courses/{course_id}/assignments/{assignment_id}/submit
POST   /courses/{course_id}/documents
DELETE /courses/{course_id}/documents/{doc_id}
```

### 15.6 Admin

```text
GET    /admin/users
POST   /admin/users
GET    /admin/users/{user_id}
GET    /admin/users/{user_id}/usage
PUT    /admin/users/{user_id}
POST   /admin/users/{user_id}/reset-password
GET    /admin/stats
GET    /admin/config
PUT    /admin/config
GET    /admin/stats/cost
GET    /admin/stats/reliability
GET    /admin/audit-logs
GET    /admin/deletions
GET    /admin/users/{user_id}/deletion-status
POST   /admin/users/{user_id}/force-purge
GET    /admin/documents
DELETE /admin/documents/{doc_id}
GET    /admin/chat-sessions
GET    /admin/chat-sessions/{session_id}
DELETE /admin/chat-sessions/{session_id}
GET    /admin/courses
GET    /admin/courses/{course_id}
PUT    /admin/courses/{course_id}
DELETE /admin/courses/{course_id}
PUT    /admin/courses/{course_id}/members
DELETE /admin/courses/{course_id}/members/{user_id}
POST   /admin/courses/{course_id}/documents
DELETE /admin/courses/{course_id}/documents/{doc_id}
```

### 15.7 Legal, Health, WebSocket

```text
GET  /legal/consents
POST /legal/consent

GET /health
GET /health/ready
GET /health/live
GET /health/deep

WS /ws
```

## 16. SSE 事件格式

### 16.1 通用 chunk

```text
data: {"type":"chunk","content":"文字片段"}
```

### 16.2 結束

```text
data: [DONE]
```

### 16.3 錯誤

```text
data: {"type":"error","code":"llm_error","message":"..."}
```

### 16.4 功能特定事件

| 功能 | Event type | 內容 |
|------|------------|------|
| RAG | `citations` | 引用來源 |
| Summary | `summary_meta` | `summary_id` |
| Quiz | `quiz_meta` | `quiz_id`、題數 |
| Mindmap | `mindmap_tree` | 完整 tree |
| Mindmap | `mindmap_patch` | append children patch |
| Mindmap | `mindmap_meta` | artifact id、format、schema version |
| Flashcards | `flashcard_meta` | 產生張數 |

## 17. WebSocket

WebSocket endpoint：

```text
WS /ws
```

認證方式：

- Authorization header bearer token，或
- query string `?token=...`

主要推播事件：

- `doc_status`：文件狀態變更，例如 converting、ocr_processing、embedding、error
- `doc_ready`：文件處理完成
- `quota_warning`：token quota 達 80% 以上
- `course_announcement`：課程公告
- `course_help_request`：課程求助
- `course_help_update`：求助狀態更新

WebSocket backend 使用 Redis pub/sub 讓不同 process 間可以推播給特定 user。

## 18. LLM 設定與成本控管

### 18.1 Provider 設定來源

`LLMClient` 會先建立預設設定：

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_CHAT_MODEL=gpt-4o-mini
LLM_VISION_MODEL=gpt-4o
LLM_EMBED_MODEL=text-embedding-3-small
```

如果 `admin_config.key = "llm_config"` 存在，DB 設定會覆蓋預設值。

### 18.2 支援的 LLM 能力

| 方法 | 用途 |
|------|------|
| `chat()` | 短回應，例如 query rewriting |
| `stream_chat()` | 主要生成，所有學習功能都使用 |
| `vision()` | OCR 圖片解析 |
| `embed()` | 文件 chunk 與 query embedding |

### 18.3 Fallback provider

Admin config 可設定 fallback providers。當 primary provider 發生：

- `APIConnectionError`
- `APITimeoutError`
- `RateLimitError`

系統會記錄 `system_events(event_type="llm_fallback")`，若有下一個 provider 則繼續嘗試。

### 18.4 Token usage 與 quota

每次 LLM 呼叫後會寫入 `token_usage`。保存欄位包含：

- feature
- tokens used
- input tokens
- output tokens
- image count
- model
- provider
- request id
- price snapshot
- cost USD

`cost_service.check_quota()` 會檢查使用者本月 token 是否超過 `users.token_quota`，超過時回傳 429。

Celery beat 每小時執行 `push_quota_warnings`，當使用者 quota percent 達 80% 以上時透過 WebSocket 推播。

## 19. Rate Limit

系統有兩層 rate limit：

1. 全域 middleware：每 client IP 每 60 秒 120 requests。
2. 特定 endpoint dependency：
   - login：每 15 分鐘 10 次
   - documents upload：每小時 10 次
   - chat message：每 10 分鐘 30 次
   - summary/quiz/mindmap/flashcards stream：每小時 5 次
   - mindmap expand：每小時 15 次

Admin 使用者會略過 endpoint-level `rate_limit()` dependency，但不一定略過全域 middleware。

## 20. 前端架構

### 20.1 Routes

前端使用 React Router。主要頁面：

| Path | 頁面 |
|------|------|
| `/login` | 登入 |
| `/register` | 註冊 |
| `/dashboard` | 儀表板 |
| `/documents` | 文件管理 |
| `/documents/:id` | 文件管理與選取文件內容 |
| `/chat` | RAG 對話 |
| `/chat/:sessionId` | 指定對話 |
| `/quiz` | 測驗列表與作答 |
| `/quiz/generate` | 測驗生成 |
| `/quiz/wrongbook` | 錯題本 |
| `/quiz/:id` | 指定測驗 |
| `/flashcards` | 閃卡 |
| `/notes` | 筆記 |
| `/courses` | 課程 |
| `/mindmap/:docId` | 心智圖 |
| `/summary/:docId` | 摘要 |
| `/settings` | 個人設定、匯出、刪除 |
| `/admin` | Admin 後台 |

### 20.2 API Client

`frontend/src/lib/api.ts`：

- `BASE_URL` 預設 `/api`
- `apiFetch()` 自動加 Authorization bearer token
- 401 時自動呼叫 `/auth/refresh`
- `uploadFile()` 與 `uploadFiles()` 使用 FormData

`frontend/src/lib/stream.ts`：

- `streamFetch()` 統一消費 SSE
- 401 時也會嘗試 refresh token
- 解析 `data: ...` event
- 遇到 `[DONE]` 結束 generator

`frontend/src/lib/ws.ts`：

- 管理 WebSocket connection
- 自動重連
- 用 event type 分派 handlers

### 20.3 Auth store

`frontend/src/store/auth.ts` 使用 Zustand 保存：

- user
- loading
- access token
- login/register/logout/loadMe actions

登入或註冊後，access token 存 localStorage。refresh token 由 backend 設成 httpOnly cookie。

## 21. 部署與本地開發

### 21.1 環境變數

`.env.example` 主要欄位：

```env
SECRET_KEY=
ENVIRONMENT=development
COOKIE_SECURE=false
LLM_API_KEY=
DATA_DIR=./data

DATABASE_URL=sqlite+aiosqlite:///./data/db/learnai.db
CHROMA_PATH=./data/chroma
REDIS_URL=redis://redis:6379/0

LLM_BASE_URL=https://api.openai.com/v1
LLM_CHAT_MODEL=gpt-4o-mini
LLM_VISION_MODEL=gpt-4o
LLM_EMBED_MODEL=text-embedding-3-small

MAX_UPLOAD_SIZE_MB=50
MAX_PAGES_PER_DOC=100
WORKER_CONCURRENCY=2
DEFAULT_USER_QUOTA_MB=500
DEFAULT_TOKEN_QUOTA=1000000
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8081,https://niu-1142-project.yuan-tw.net
```

Production 時必須設定安全的 `SECRET_KEY`。若 `ENVIRONMENT=production` 且使用預設 secret，後端會拒絕啟動。

### 21.2 啟動

```bash
cp .env.example .env
docker compose up -d --build
```

開發 hot reload：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 21.3 常用維運指令

```bash
docker compose ps
docker compose logs -f backend worker
docker compose restart backend
docker compose exec backend python scripts/create_admin.py
docker compose exec backend pytest
docker compose exec frontend npm run lint
```

### 21.4 Health checks

| Endpoint | 用途 |
|----------|------|
| `/health/live` | liveness，輕量檢查 |
| `/health/ready` | readiness，檢查依賴狀態 |
| `/health` | 一般 health report |
| `/health/deep` | admin-only，包含 LLM 深度檢查 |

Compose backend healthcheck 使用 `/health/live`。

## 22. 測試狀態

目前 repo 內有後端測試：

- `backend/tests/test_chunker_json.py`
- `backend/tests/test_learning_service.py`

建議測試用 Docker Compose 執行：

```bash
docker compose exec backend pytest
```

前端可做 TypeScript 型別檢查：

```bash
docker compose exec frontend npm run lint
```

## 23. 安全重點

目前已實作或設計上的安全點：

- bcrypt hash password
- JWT access token + httpOnly refresh cookie
- inactive user 不可登入或使用 token
- Admin API 使用 `require_admin`
- 課程操作使用 `require_member()` 與 `require_role()`
- 文件路徑使用 `safe_join()`
- 上傳副檔名白名單
- 上傳 MIME type 基本檢查
- 上傳大小限制
- 使用者儲存 quota
- token quota
- rate limit
- Nginx 設定 `client_max_body_size 50m`
- Nginx 關閉 API proxy buffering，避免 SSE 被緩衝
- 管理與隱私操作寫 audit log

需要注意的地方：

- SQLite 適合課程專案與小型部署；高併發 production 建議切 PostgreSQL。
- ChromaDB PersistentClient 與多 process 共享目錄時要留意並發寫入，目前用 FileLock 包住 upsert/delete。
- PPTX/DOCX 轉換依賴 LibreOffice，Docker image 需要包含該套件。
- OpenAI-compatible provider 的 response usage 欄位可能不同，系統會在缺 usage 時用字元數估 token。

## 24. 典型使用流程

### 24.1 學生個人學習

1. 註冊或登入。
2. 到文件頁同意著作權聲明。
3. 上傳 PDF。
4. 等待 WebSocket 顯示處理完成。
5. 到 Chat 建立對話，選擇該文件。
6. 發問，取得 streaming 回答與引用頁碼。
7. 到 Summary 產生摘要。
8. 到 Quiz 生成測驗並作答。
9. 從錯題本或文件生成 Flashcards。
10. 用 Notes 保存重點。
11. Dashboard 查看今日目標、待複習閃卡與課程活動。

### 24.2 教師課程教學

1. teacher/admin 建立課程。
2. 系統產生 join code。
3. 學生用 join code 加入。
4. 教師上傳文件並處理完成。
5. 教師把文件加入課程。
6. 課程成員可針對共享文件聊天、摘要、測驗。
7. 教師發布公告與作業。
8. 教師生成測驗並發布到課程。
9. 學生作答後，教師在 progress 查看分數、活動與風險。
10. 學生可提出 help request，教師/TA 處理。

### 24.3 Admin 維運

1. 進入 `/admin`。
2. 查看系統統計與成本。
3. 調整 LLM config 或 fallback provider。
4. 管理使用者角色、啟用狀態與 quota。
5. 檢查文件、對話與課程資料。
6. 查看 audit logs 與 reliability events。
7. 處理資料刪除或強制清除。

## 25. 已知限制與後續建議

- 目前資料庫初始化偏向開發方便，production 建議加入 Alembic migration 流程。
- SQLite 在大量課程與高併發寫入下可能不夠，production 建議 PostgreSQL。
- OCR 使用 Vision LLM，成本與速度取決於 provider；大量文件需要批次控制與更細的 retry/queue 策略。
- ChromaDB local persistent mode 適合單機部署；多機部署建議改成 dedicated vector DB 或 Chroma server 架構。
- 測驗 JSON、心智圖 JSON 雖有 parser 保護，仍需要針對 LLM 格式錯誤做更完整的修復策略。
- Citation support 目前是簡易文字比對，不等同嚴格事實驗證。
- 前端 UI 已涵蓋主要流程，但大型課程情境還可以補強分頁、搜尋、批次操作與教師分析視覺化。
