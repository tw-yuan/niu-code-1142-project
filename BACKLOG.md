# BACKLOG.md — LearnAI 功能待辦清單

> 本文件為傳遞給 AI coding agent 的結構化功能清單。
> 每個 Issue 包含背景、驗收條件、技術提示，agent 可直接依此開始實作。
> 參照 SPEC.md（系統規格）與 AGENTS.md（開發規範）作為基礎上下文。

---

## 讀取本文件的方式

- `Priority` 欄位：`P1` = 應優先實作，`P2` = 核心功能完成後實作，`P3` = 最後實作
- `Scope` 欄位：`backend` / `frontend` / `both`
- `Depends` 欄位：必須先完成的 Issue ID
- 每個 Issue 的 `AC`（Acceptance Criteria）為最低完成標準，通過即可關閉

---

## P1 — 高優先（穩定性與費用控管）

---

### ISSUE-001：費用監控儀表板

**Priority:** P1
**Scope:** both
**Depends:** 無（需先有 `token_usage` 表，SPEC § 11 已定義）

**背景**
Vision OCR 使用 gpt-4o，每頁約 $0.01 USD。若無費用控管，單次壓力測試即可讓 API Key 超額。目前 `token_usage` 表已有記錄但 Admin UI 沒有對應頁面。

**需要實作**

後端：
- `GET /admin/stats/cost` 回傳以下結構：
  ```json
  {
    "today": { "total_usd": 0.42, "by_feature": { "ocr": 0.30, "chat": 0.08, "embed": 0.04 } },
    "this_month": { "total_usd": 12.50, "by_feature": {...} },
    "top_users": [{ "user_id": "...", "username": "...", "total_usd": 2.10 }],
    "daily_series": [{ "date": "2026-06-16", "total_usd": 0.42 }]
  }
  ```
- USD 換算：從 `admin_config` 讀取各 model 的 per-token 價格設定，預設值：
  - `gpt-4o` input: $0.0025/1K tokens, output: $0.01/1K tokens
  - `gpt-4o-mini` input: $0.00015/1K tokens, output: $0.0006/1K tokens
  - `text-embedding-3-small`: $0.00002/1K tokens
- `PUT /admin/config` 支援更新 `cost_per_1k_tokens` 欄位

前端（`/admin` 頁面新增 Cost 分頁）：
- 今日 / 本月費用總覽卡片
- 各 feature 費用佔比長條圖（Recharts `BarChart`）
- 每日費用趨勢折線圖（最近 30 天）
- 費用最高的使用者 Top 10 表格

**AC（驗收條件）**
- [ ] `GET /admin/stats/cost` 回應時間 < 500ms
- [ ] 費用計算與 `token_usage` 表資料一致
- [ ] 前端圖表正確渲染，無 console error
- [ ] 只有 `role=admin` 的使用者可存取，一般使用者回傳 403

---

### ISSUE-002：超額自動停用與警示

**Priority:** P1
**Scope:** backend
**Depends:** ISSUE-001（需費用計算邏輯）

**背景**
每位使用者有 `token_quota` 上限，但目前沒有實際執行停用邏輯，配額只是存在 DB 的數字。

**需要實作**

- 在 `LLMClient.chat()`、`LLMClient.vision()`、`LLMClient.embed()` 呼叫前，加入配額檢查：
  ```python
  async def _check_quota(self, user_id: str, feature: str) -> None:
      used = await self._get_monthly_usage(user_id)
      limit = await self._get_user_quota(user_id)
      if used >= limit:
          raise HTTPException(status_code=429, detail={
              "code": "quota_exceeded",
              "message": "本月 token 配額已用完，請聯絡管理員",
              "used": used,
              "limit": limit,
          })
  ```
- Celery Beat 定時任務（每小時執行）：掃描本月用量超過配額 80% 的使用者，發送警告 event 至 WebSocket（使用者下次開啟頁面時看到 banner）
- `GET /auth/me` 回應新增 `quota_status` 欄位：
  ```json
  {
    "token_quota": 1000000,
    "token_used_this_month": 850000,
    "quota_percent": 85,
    "quota_status": "warning"  // "ok" | "warning" | "exceeded"
  }
  ```
- 前端：`quota_percent >= 80` 時頁面頂部顯示黃色 banner；`>= 100` 時顯示紅色 banner 並停用所有 AI 功能按鈕

**AC**
- [ ] 超額使用者呼叫任何 LLM 端點均回傳 429，錯誤碼為 `quota_exceeded`
- [ ] 80% 警告 banner 正確顯示
- [ ] Admin 可透過 `PUT /admin/users/{id}` 調高配額後立即生效
- [ ] 配額檢查不影響非 LLM 端點（上傳、登入等）

---

### ISSUE-003：多 LLM 後端 Fallback 機制

**Priority:** P1
**Scope:** backend
**Depends:** 無

**背景**
若 OpenAI API 服務中斷，整個平台即不可用。需要支援備援 LLM 後端。

**需要實作**

- `admin_config` 新增 `fallback_providers` 欄位：
  ```json
  {
    "chat": {
      "primary": { "base_url": "https://api.openai.com/v1", "api_key": "sk-...", "model": "gpt-4o-mini" },
      "fallback": [
        { "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "api_key": "...", "model": "gemini-1.5-flash" }
      ]
    }
  }
  ```
- `LLMClient` 實作 fallback 邏輯：
  ```python
  async def _call_with_fallback(self, providers, call_fn):
      for i, provider in enumerate(providers):
          try:
              return await call_fn(provider)
          except (APIConnectionError, APITimeoutError, RateLimitError) as e:
              if i == len(providers) - 1:
                  raise  # 全部失敗才往上拋
              logger.warning(f"Provider {provider['model']} failed, trying fallback: {e}")
              continue
  ```
- Fallback 觸發條件：`APIConnectionError`、`APITimeoutError`、`RateLimitError`（不含 `AuthenticationError`，那代表 key 設定錯誤，fallback 沒意義）
- 每次觸發 fallback 寫入 `system_events` 表（新建）供 Admin 檢視
- `GET /admin/stats/reliability` 回傳最近 7 天的 fallback 觸發次數與原因

**AC**
- [ ] Primary provider 逾時 10 秒後自動切換 fallback
- [ ] Fallback 觸發時 Streaming 不中斷（fallback provider 接續輸出）
- [ ] 只設定 primary、無 fallback 時，行為與原本一致
- [ ] Admin UI 可新增 / 刪除 fallback provider

---

### ISSUE-004：精細 Rate Limiting

**Priority:** P1
**Scope:** backend
**Depends:** 無

**背景**
目前只有 60 req/min/IP 的全域限制。OCR 端點費用高昂，需要獨立更嚴格的限制。

**需要實作**

使用 Redis Sliding Window 演算法，在 `dependencies.py` 新增可組合的 rate limit 依賴：

```python
def rate_limit(key_prefix: str, limit: int, window_seconds: int):
    """
    回傳 FastAPI Depends，依 user_id（已登入）或 IP（未登入）計數。
    超過限制回傳 429，header 含 Retry-After。
    """
    async def _check(
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
    ):
        ...
    return Depends(_check)
```

各端點限制設定：

| 端點 | 限制 | 視窗 |
|------|------|------|
| `POST /documents/upload` | 10 次/小時/使用者 | 3600s |
| `POST /chat/sessions/{id}/message` | 30 次/10 分鐘/使用者 | 600s |
| `POST /summary/stream` | 5 次/小時/使用者 | 3600s |
| `POST /quiz/stream` | 5 次/小時/使用者 | 3600s |
| `POST /mindmap/stream` | 5 次/小時/使用者 | 3600s |
| `POST /flashcards/stream` | 5 次/小時/使用者 | 3600s |
| `POST /auth/login` | 10 次/15 分鐘/IP | 900s |
| 全域 | 120 次/分鐘/IP | 60s |

Response header（符合 RFC 6585）：
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 12
X-RateLimit-Reset: 1718500000
Retry-After: 342  # 僅在 429 時出現
```

**AC**
- [ ] 各端點超過限制時回傳 429，含 `Retry-After` header
- [ ] User 維度與 IP 維度計數獨立，已登入使用者以 user_id 計數
- [ ] Admin 使用者豁免所有 rate limit
- [ ] Redis key 格式：`rl:{key_prefix}:{identifier}`，TTL 等於 window_seconds

---

### ISSUE-005：系統健康監控端點

**Priority:** P1
**Scope:** backend
**Depends:** 無

**背景**
線上部署後需要外部監控工具（如 Uptime Kuma）能探測系統是否正常。

**需要實作**

- `GET /health`（公開，無需認證）：
  ```json
  {
    "status": "ok",  // "ok" | "degraded" | "down"
    "version": "3.0.0",
    "checks": {
      "database": { "status": "ok", "latency_ms": 2 },
      "redis": { "status": "ok", "latency_ms": 1 },
      "chroma": { "status": "ok", "doc_count": 1523 },
      "celery": { "status": "ok", "active_tasks": 2, "queued_tasks": 0 },
      "llm_api": { "status": "ok", "latency_ms": 312 }
    }
  }
  ```
- HTTP status code：全部 ok → 200，任一 degraded → 200，任一 down → 503
- LLM API 檢查：發送一個最小 embedding request（單一字元），計算延遲
- Celery 檢查：透過 `celery_app.control.inspect().active()` 確認 worker 在線
- 逾時保護：每個子檢查最多等待 3 秒，超時標記為 `degraded`

**AC**
- [ ] 所有元件正常時回傳 200 + `status: ok`
- [ ] Redis 斷線時回傳 503 + `status: down`
- [ ] 端點回應時間 < 5 秒（含所有子檢查）
- [ ] 不在 log 中記錄此端點的成功請求（避免 log 噪音）

---

## P2 — 中優先（使用者體驗提升）

---

### ISSUE-006：個人筆記系統

**Priority:** P2
**Scope:** both
**Depends:** 無

**背景**
學生在閱讀 AI 生成的摘要或進行 RAG 問答時，需要能記錄自己的理解與補充，並與來源頁碼關聯。

**需要實作**

DB（新增 `notes` 表）：
```sql
CREATE TABLE notes (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    doc_id      TEXT REFERENCES documents(id) ON DELETE SET NULL,
    session_id  TEXT REFERENCES chat_sessions(id) ON DELETE SET NULL,
    content     TEXT NOT NULL,
    source_page INTEGER,
    source_type TEXT,  -- "chat" | "summary" | "manual"
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX idx_notes_user_doc ON notes(user_id, doc_id);
```

後端端點：
```
POST   /notes               新增筆記
GET    /notes               列出（?doc_id=&session_id=）
PUT    /notes/{id}          更新內容
DELETE /notes/{id}
GET    /notes/export/{doc_id}   匯出為 Markdown
```

前端整合：
- 對話介面：每則 AI 回應右側出現「記筆記」icon，點擊後側邊滑出筆記欄，預填來源資訊
- 摘要頁面：每個段落右側可點擊新增筆記，自動記錄段落對應頁碼
- `/notes` 獨立頁面：以文件為分組顯示所有筆記，支援搜尋、匯出 Markdown

**AC**
- [ ] 筆記與來源（doc_id + page）成功關聯
- [ ] `GET /notes?doc_id=x` 只回傳該使用者的筆記（403 隔離）
- [ ] Markdown 匯出格式正確，含來源標示
- [ ] 筆記內容支援基本 Markdown 語法（前端以 `react-markdown` 渲染）

---

### ISSUE-007：學習目標設定與每日任務

**Priority:** P2
**Scope:** both
**Depends:** 無

**背景**
學生上傳文件後缺乏引導，不知道該從哪裡開始學習。設定目標後系統可自動規劃每日任務。

**需要實作**

DB（新增 `learning_goals` 表）：
```sql
CREATE TABLE learning_goals (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    doc_id      TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    target_date TEXT NOT NULL,  -- ISO8601 date
    focus_hint  TEXT,           -- 學生輸入：「重點在第三章排序演算法」
    status      TEXT NOT NULL DEFAULT 'active',  -- active | completed | abandoned
    created_at  TEXT NOT NULL
);
```

後端：
- `POST /goals`、`GET /goals`、`PUT /goals/{id}`、`DELETE /goals/{id}`
- `GET /goals/today` 回傳今日推薦任務清單：
  ```json
  {
    "tasks": [
      { "type": "flashcard_review", "due_count": 8, "doc_title": "演算法課程" },
      { "type": "read_summary", "doc_id": "...", "chapter": "第三章" },
      { "type": "take_quiz", "suggested_doc_id": "...", "suggested_count": 5 }
    ],
    "streak_days": 7
  }
  ```
- 任務生成邏輯（後端純計算，無需 LLM）：
  - 距離 `target_date` 天數 / 文件 chunk 總數 = 每日建議閱讀量
  - 今日到期閃卡數（SM-2 `next_review <= today`）
  - 尚未生成摘要的章節

前端：
- 文件上傳完成後，引導使用者設定學習目標（可跳過）
- Dashboard 首頁顯示「今日任務」卡片，點擊直接進入對應功能

**AC**
- [ ] 設定目標後，`GET /goals/today` 回傳非空的任務清單
- [ ] `target_date` 過去的目標自動標記為 `abandoned`
- [ ] 今日任務卡片在 Dashboard 正確顯示
- [ ] 一份文件可設定多個目標（例如不同考試）

---

### ISSUE-008：課程空間（Course Space）

**Priority:** P2
**Scope:** both
**Depends:** 無

**背景**
目前教師完全沒有使用本平台的方式。課程空間允許教師建立課程、上傳共用資料，學生加入後可在 RAG 問答中存取教師文件。

**需要實作**

DB（新增 `courses`、`course_members`、`course_documents` 表）：
```sql
CREATE TABLE courses (
    id           TEXT PRIMARY KEY,
    owner_id     TEXT NOT NULL REFERENCES users(id),
    title        TEXT NOT NULL,
    description  TEXT,
    join_code    TEXT UNIQUE NOT NULL,  -- 6 碼邀請碼
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL
);

CREATE TABLE course_members (
    course_id  TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT NOT NULL DEFAULT 'student',  -- student | instructor
    joined_at  TEXT NOT NULL,
    PRIMARY KEY (course_id, user_id)
);

CREATE TABLE course_documents (
    course_id  TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    doc_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    added_at   TEXT NOT NULL,
    PRIMARY KEY (course_id, doc_id)
);
```

後端端點：
```
POST   /courses                     建立課程（任何使用者）
GET    /courses                     列出我加入的課程
GET    /courses/{id}
DELETE /courses/{id}                只有 owner 可刪除
POST   /courses/join                以 join_code 加入課程，body: {join_code: "ABC123"}
POST   /courses/{id}/documents      加入文件到課程（owner/instructor）
DELETE /courses/{id}/documents/{doc_id}
GET    /courses/{id}/members
```

RAG 整合：
- `POST /chat/sessions` body 新增 `course_id` 欄位
- 若 `course_id` 有值，RAG 向量搜尋範圍自動擴展到該課程的所有文件
- 課程文件的 ChromaDB metadata 新增 `course_id` 欄位，`where` filter 改為：
  ```python
  {"$or": [{"user_id": {"$eq": user_id}}, {"course_id": {"$eq": course_id}}]}
  ```

前端：
- `/courses` 課程列表頁，可建立課程或以邀請碼加入
- 課程詳情頁：成員列表、課程文件列表、邀請碼顯示（QR code 可選）
- 對話新建時可選擇「個人文件」或「課程文件」

**AC**
- [ ] 學生以邀請碼加入後，可在 RAG 問答中搜尋課程文件
- [ ] 學生無法看到課程內其他學生的個人文件
- [ ] 課程 owner 刪除文件後，學生 session 中該文件不再出現在搜尋結果
- [ ] `GET /courses/{id}` 非成員回傳 403

---

### ISSUE-009：知識覆蓋熱力圖

**Priority:** P2
**Scope:** both
**Depends:** ISSUE-007（學習目標），ISSUE-006（筆記，可選）

**背景**
Dashboard 目前只有數字統計，缺乏直覺的學習狀況視覺化。熱力圖讓學生一眼看出哪些章節熟悉、哪些薄弱。

**需要實作**

後端：
- `GET /documents/{id}/coverage` 回傳：
  ```json
  {
    "chapters": [
      {
        "title": "第一章 排序演算法",
        "page_range": [1, 15],
        "quiz_attempts": 3,
        "quiz_score_avg": 0.85,
        "flashcard_count": 12,
        "flashcard_mastered": 10,
        "chat_mentions": 5,
        "coverage_score": 0.82  // 0.0~1.0，後端計算
      }
    ]
  }
  ```
- `coverage_score` 計算公式（後端，無需 LLM）：
  ```
  score = (quiz_score_avg × 0.4) + (flashcard_mastered/flashcard_count × 0.4) + (min(chat_mentions/3, 1.0) × 0.2)
  ```
- 章節邊界偵測：從文件的 chunk metadata 中的頁碼範圍，搭配 OCR 文字中的標題關鍵詞（`=== 第 N 頁 ===` 後面第一個以數字開頭的行）自動切分

前端：
- 文件詳情頁新增「學習覆蓋度」分頁
- 以顏色深淺的橫向長條表示各章節熟悉度（不需要熱力圖套件，用 Tailwind 動態 class 即可）
- 點擊章節 → 跳轉至 RAG 對話並自動帶入「請幫我複習 {chapter_title}」

**AC**
- [ ] 有測驗記錄的章節 `coverage_score` > 0
- [ ] 完全未互動的章節 `coverage_score` = 0，顯示最淺色
- [ ] 點擊章節跳轉對話功能正常
- [ ] 無章節資料時顯示「尚無學習記錄」而非空白或錯誤

---

### ISSUE-010：AI 生成內容免責標示

**Priority:** P2
**Scope:** frontend
**Depends:** 無

**背景**
所有 AI 生成的內容（摘要、測驗、心智圖、閃卡）都可能包含錯誤或幻覺，應有明確標示以符合學術誠信要求。

**需要實作**

前端統一元件 `<AIGeneratedBadge />`：
```tsx
// components/app/AIGeneratedBadge.tsx
// 顯示一個小 banner：「由 AI 生成，內容僅供參考，請自行驗證」
// 使用 Info icon（lucide-react），點擊展開說明
// 不使用 emoji
```

套用位置：
- 摘要頁面：標題下方
- 測驗頁面：題目上方（每題一個小 badge，或整體一個）
- 心智圖頁面：工具列旁
- 閃卡背面：底部小字
- RAG 對話回應：每則 assistant 訊息底部（使用更小的 inline 版本）

RAG 對話額外規則：
- 嚴格模式：不顯示 badge（內容完全來自文件，不是 AI 創作）
- 增強模式：顯示 badge
- 蘇格拉底模式：顯示「AI 引導問答，答案由您作答」

**AC**
- [ ] 所有 AI 生成內容頁面均有 badge
- [ ] Badge 不遮擋主要內容
- [ ] RAG 嚴格模式下不顯示 badge
- [ ] Badge 在 light / dark mode 下均清晰可讀

---

## P3 — 低優先（法規合規）

---

### ISSUE-011：審計日誌（Audit Log）

**Priority:** P3
**Scope:** backend
**Depends:** 無

**背景**
需記錄所有敏感操作以應對資安事件調查，日誌需不可竄改（append-only）。

**需要實作**

DB（新增 `audit_logs` 表，不允許 UPDATE / DELETE）：
```sql
CREATE TABLE audit_logs (
    id          TEXT PRIMARY KEY,
    user_id     TEXT,           -- 可為 NULL（未登入操作）
    action      TEXT NOT NULL,  -- 見下方 Action 清單
    resource    TEXT,           -- 操作對象，如 "document:uuid"
    ip_address  TEXT,
    user_agent  TEXT,
    detail      TEXT,           -- JSON，額外資訊
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at);
CREATE INDEX idx_audit_action ON audit_logs(action, created_at);
```

需記錄的 Action 清單：
```
auth.register        auth.login           auth.login_failed
auth.logout          auth.token_refresh

document.upload      document.delete      document.download

admin.user_update    admin.config_update  admin.user_disable
admin.quota_update

chat.session_create  chat.session_delete

data.export          data.delete_request
```

實作方式：
- 在 `dependencies.py` 新增 `AuditLogger` class
- 透過 FastAPI `BackgroundTasks` 非同步寫入（不阻塞請求）
- 敏感欄位（密碼、API Key）不得進入 `detail` 欄位

後端端點（Admin only）：
```
GET /admin/audit-logs
  ?user_id=&action=&from=&to=&limit=50&offset=0
```

**AC**
- [ ] 上述所有 Action 在對應操作發生時均有記錄
- [ ] `audit_logs` 表不存在 UPDATE 或 DELETE 的程式碼路徑
- [ ] `GET /admin/audit-logs` 支援 `action` 和 `user_id` 過濾
- [ ] `ip_address` 正確取得（考慮 Nginx 反向代理的 `X-Forwarded-For`）
- [ ] 密碼、API Key 不出現在任何 `detail` 欄位

---

### ISSUE-012：個人資料保留政策與刪除機制

**Priority:** P3
**Scope:** both
**Depends:** ISSUE-011（審計日誌，刪除操作需記錄）

**背景**
符合台灣個人資料保護法，使用者有權要求刪除所有個人資料。帳號刪除後 30 天內需徹底清除。

**需要實作**

刪除請求流程：
1. 使用者在 `/settings` 頁面提交「刪除我的帳號」請求
2. 系統寄送確認 email（若有設定 SMTP）或顯示確認碼（無 SMTP 時）
3. 確認後帳號立即停用（`is_active = 0`），排程 30 天後的完整刪除任務
4. 30 天內使用者可聯絡 Admin 取消

完整刪除的範圍（Celery 定時任務）：
```python
async def purge_user_data(user_id: str):
    # 1. 刪除 ChromaDB 向量（where user_id = user_id）
    await chroma_service.delete_user_chunks(user_id)

    # 2. 刪除本地檔案
    shutil.rmtree(f"{DATA_DIR}/uploads/{user_id}", ignore_errors=True)

    # 3. 刪除 DB 資料（CASCADE 會處理子表）
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()

    # 4. 寫入 audit log（保留此筆記錄，user_id 可以是匿名化 hash）
    await audit_logger.log("data.purge_complete", resource=f"user:{hash(user_id)}")
```

資料匯出功能（GDPR right to data portability）：
- `POST /auth/me/export-request` 觸發非同步任務
- 任務完成後可透過 `GET /auth/me/export-download` 下載 ZIP 檔，含：
  - `profile.json`（使用者基本資料）
  - `documents.json`（文件清單，不含原始檔案）
  - `chat_history.json`（所有對話記錄）
  - `flashcards.json`
  - `quiz_attempts.json`
  - `notes.json`
- ZIP 檔有效期 24 小時，儲存於 `{DATA_DIR}/exports/`

後端端點：
```
POST   /auth/me/delete-request         提交刪除請求
POST   /auth/me/delete-confirm         以確認碼確認（觸發停用 + 排程）
POST   /auth/me/delete-cancel          取消（30 天內）
POST   /auth/me/export-request         觸發資料匯出
GET    /auth/me/export-download        下載 ZIP（需 token）

GET    /admin/users/{id}/deletion-status   查看刪除請求狀態
POST   /admin/users/{id}/force-purge       立即清除（不等 30 天）
```

前端：
- `/settings` 頁面最底部「危險區域」區塊
- 刪除流程有明確的確認步驟（輸入 username 確認）
- 帳號停用後自動登出並顯示說明頁面

**AC**
- [ ] 刪除確認後帳號立即無法登入
- [ ] 30 天後 Celery 任務自動執行清除，涵蓋 ChromaDB、本地檔案、DB 所有相關記錄
- [ ] 清除完成後 `audit_logs` 中有對應記錄
- [ ] 資料匯出 ZIP 包含所有 AC 要求的檔案，格式正確
- [ ] `GET /auth/me/export-download` 超過 24 小時回傳 410 Gone

---

### ISSUE-013：著作權免責聲明

**Priority:** P3
**Scope:** both
**Depends:** 無

**背景**
學生上傳受著作權保護的文件（教科書 PDF）存在法律風險，平台需有免責機制。

**需要實作**

DB：
```sql
CREATE TABLE legal_consents (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL,  -- "copyright_declaration"
    consented_at TEXT NOT NULL,
    ip_address TEXT
);
```

流程：
- 使用者首次上傳文件前，顯示著作權聲明 modal：
  ```
  上傳前請確認：
  您上傳的文件必須為您合法持有的資料，或已獲得著作權人授權。
  本平台不儲存或散布受著作權保護的內容，所有文件僅供您個人學習使用。
  違反著作權法的責任由上傳者自行承擔。
  ```
- 勾選「我已了解並同意」後才能上傳，同意記錄存入 `legal_consents`
- 已同意過的使用者不再顯示（每位使用者只需同意一次）
- `POST /documents/upload` 後端驗證：使用者若無 `copyright_declaration` 記錄，回傳 403 + `{"code": "consent_required"}`

後端端點：
```
POST /legal/consent    body: {consent_type: "copyright_declaration"}
GET  /legal/consents   回傳目前使用者已同意的項目清單
```

**AC**
- [ ] 首次上傳前必須同意，否則前端阻擋上傳
- [ ] 後端雙重驗證，即使繞過前端也回傳 403
- [ ] 已同意使用者不再重複顯示 modal
- [ ] 同意記錄含 `consented_at` 與 `ip_address`

---

## 附錄 A：不實作的功能清單

以下功能經決策後**不納入本專案**，未來如需實作請另立新文件：

| 功能 | 排除原因 |
|------|---------|
| 離線模式 / Service Worker | 增加複雜度，線上展示不需要 |
| PWA / Web Push | 同上 |
| Prompt 版本管理 / A/B 測試 | 開發者工具，課程專案範圍外 |
| 自動化 Evals | 需要額外評估資料集，超出範圍 |
| OpenTelemetry 追蹤 | 運維工具，課程專案範圍外 |
| Plugin 架構 | 過度設計，目前格式固定 |
| CI/CD Pipeline | 課程展示手動部署即可 |
| SSO / SAML / OIDC | 無學校系統對接需求 |
| CDN 靜態資產分流 | 單機部署不需要 |
| 水平擴展設計 | 單機 Docker Compose 足夠 |
| Private LLM 部署 | 使用外部 API 即可 |

---

## 附錄 B：與 SPEC.md 的關係

本 BACKLOG.md 為 SPEC.md v3.0.0 的**增量功能清單**。

- SPEC.md 定義的功能（RAG 問答、摘要、測驗、心智圖、閃卡等）為**基礎功能，優先於本清單實作**。
- 本清單的 Issue 均以 SPEC.md 定義的架構為前提，不修改核心架構。
- 若本清單與 SPEC.md 有衝突，以**本文件的描述為準**（本文件較新）。

---

## 附錄 C：Issue 狀態追蹤

| Issue | 標題 | Priority | 狀態 |
|-------|------|----------|------|
| ISSUE-001 | 費用監控儀表板 | P1 | `done` |
| ISSUE-002 | 超額自動停用與警示 | P1 | `done` |
| ISSUE-003 | 多 LLM 後端 Fallback | P1 | `done` |
| ISSUE-004 | 精細 Rate Limiting | P1 | `done` |
| ISSUE-005 | 系統健康監控端點 | P1 | `done` |
| ISSUE-006 | 個人筆記系統 | P2 | `done` |
| ISSUE-007 | 學習目標與每日任務 | P2 | `done` |
| ISSUE-008 | 課程空間 | P2 | `done` |
| ISSUE-009 | 知識覆蓋熱力圖 | P2 | `done` |
| ISSUE-010 | AI 生成內容免責標示 | P2 | `done` |
| ISSUE-011 | 審計日誌 | P3 | `done` |
| ISSUE-012 | 資料保留政策與刪除 | P3 | `done` |
| ISSUE-013 | 著作權免責聲明 | P3 | `done` |

Agent 完成一個 Issue 後，將對應列的 `todo` 改為 `done`。
