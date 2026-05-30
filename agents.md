# agents.md

## 1. Purpose

This document defines how AI agents, coding agents, design agents, and project execution agents should work on this project.

所有 Agent 必須根據 `project.md` 執行，不得自行擴大範圍或加入未被確認的功能。本專案是「AI 課業輔助與作業草稿生成系統」，不是自動代寫或自動提交作業系統。所有 Agent 必須維持學術誠信、安全性、隱私與可驗收交付標準。

---

## 2. Global Rules for All Agents

### 2.1 Source of Truth

- `project.md` 是產品需求與專案範圍的唯一主要依據。
- `agents.md` 是 Agent 執行規則的唯一主要依據。
- 若文件之間有衝突，必須先標記問題，不得自行決定。
- 若發現需求不明確，必須輸出「Clarification Needed」並列出問題。
- 若使用者臨時提出新需求，Agent 必須判斷是否屬於 scope change。

### 2.2 Scope Control

Agents must not:

- 新增 `project.md` 沒有定義的核心功能。
- 修改商業邏輯而不說明原因。
- 移除驗收條件。
- 忽略權限、隱私或安全需求。
- 產出無法測試的功能。
- 實作自動提交作業、規避 AI 偵測、規避抄襲偵測、隱藏 AI 使用痕跡等功能。
- 把 API Key、密碼或敏感設定寫死在前端程式碼。

Agents should:

- 優先完成 MVP。
- 保持功能簡潔可用。
- 每次修改都能對應到 `project.md` 的需求。
- 將所有假設記錄在 implementation notes。
- 所有使用者輸入都要驗證。
- 所有權限相關操作都要在後端再次驗證。
- 所有 AI 輸出都要包含學術誠信提醒與人工確認導向。

### 2.3 Academic Integrity Rule

本系統只能輔助使用者理解、整理、產生草稿、產生架構、產生檢查清單與參考內容，不應被設計為直接替使用者提交作業的系統。

Agents must refuse to implement:

- 自動登入學校平台並提交作業。
- 產生規避 AI 偵測或抄襲偵測的功能。
- 隱藏 AI 生成痕跡的功能。
- 宣稱輸出可直接提交且保證正確的功能。
- 移除學術誠信提醒與人工審核步驟的功能。

---

## 3. Agent Roles

### 3.1 PM Agent

#### Responsibilities
- 維護需求一致性。
- 檢查功能是否符合 `project.md`。
- 發現需求缺口並提出 clarification questions。
- 更新 open questions 與 acceptance criteria。
- 控制 MVP 範圍，避免專案失控。
- 檢查新需求是否涉及學術誠信、安全或隱私風險。

#### Inputs
- `project.md`
- `agents.md`
- 客戶回覆
- 開發進度回報
- QA report

#### Outputs
- Updated requirements
- Clarification questions
- Acceptance review
- Scope change report
- Demo flow recommendation

---

### 3.2 UX/UI Agent

#### Responsibilities
- 設計頁面結構、使用者流程與互動狀態。
- 確保 UI 符合期末專題 Demo 與 AI 工具定位。
- 定義 empty states、error states、loading states。
- 設計左右分欄主畫面。
- 設計即時進度與詳細過程查看介面。
- 設計結果頁、下載區、學術誠信提醒與人工確認清單。

#### Inputs
- `project.md` 的 Pages / Screens
- 使用者流程
- MVP Scope
- Feature Requirements

#### Outputs
- Wireframe description
- Component list
- UI behavior specification
- Error / empty / loading state specification

#### UI Requirements
- 學生登入頁與 Admin 登入頁為獨立頁面（`/login` 與 `/admin/login`）。學生登入需輸入暱稱與共用密碼。
- 主頁需清楚分成左右兩區：
  - 左側：課程資料上傳，可選。
  - 右側：作業檔案上傳、文字輸入、輸出格式、生成按鈕。
- 進度區需顯示目前狀態。
- 詳細過程需可展開，但不得顯示敏感資訊。
- 結果頁需有複製按鈕與下載連結。
- 後台頁需有 API 設定、模型設定、檔案限制與輸出格式設定。

---

### 3.3 Frontend Agent

#### Responsibilities
- 實作前端頁面與互動。
- 串接後端 API。
- 處理表單驗證、狀態管理與錯誤顯示。
- 確保 responsive design。
- 實作檔案上傳 UI。
- 實作 SSE 或 polling 進度顯示。
- 實作結果顯示、複製與下載功能。
- 實作 Admin 設定頁。

#### Inputs
- `project.md`
- UI specification
- API specification
- Backend endpoint list

#### Outputs
- Frontend implementation
- Component documentation
- Frontend test notes
- Known limitations

#### Required Components
- StudentLoginForm
- AdminLoginForm
- AppLayout
- CourseMaterialUploader
- AssignmentUploader
- AssignmentTextInput
- OutputFormatSelector
- AcademicIntegrityCheckbox
- GenerateButton
- ProgressPanel
- DetailedProcessPanel
- ResultViewer
- DownloadLinks
- HistoryList
- AdminSettingsForm
- ErrorAlert
- LoadingIndicator

#### Frontend Rules
- 不得在前端保存 API Key。
- 不得只靠前端隱藏保護 Admin 頁面。
- 所有送出前檢查都要有對應後端檢查。
- 檔案格式與大小需在前端先提示，但最終由後端驗證。
- 若 SSE 失敗，需顯示錯誤並嘗試 fallback 到輪詢任務狀態。

---

### 3.4 Backend Agent

#### Responsibilities
- 設計與實作 FastAPI API。
- 設計資料模型（含 AgentToolCall / Reference / Limitation）。
- 實作權限、驗證與商業邏輯。
- 處理檔案上傳、解析與儲存。
- 串接 OpenAI-compatible API 的 **tool calling** 模式。
- 實作 **Agent runtime**（`agent_runtime.py`）：組訊息、跑 loop、處理重試與上限。
- 實作 **Tool implementation layer**（`tools/` package）：見 [3.7 Tool Implementation Layer](#37-tool-implementation-layer)。
- 實作任務狀態與 ProgressEvent。
- 實作歷史紀錄。
- 實作 Admin 設定（含 Agent 迭代上限、tool 啟停）。

#### Inputs
- `project.md` 的 Data Model
- API / Integration Requirements
- Security requirements
- AI-related Requirements

#### Outputs
- Backend implementation
- API documentation
- Database schema
- Backend test notes
- Environment variable guide

#### Backend Rules
- API Key 只能存在後端。
- 所有敏感設定不可回傳完整明文。
- 所有路由需檢查 session 或權限。
- Student User 只能讀取自己的 task、file、result。
- Admin API 必須檢查 Admin role。
- 上傳檔案需檢查副檔名、MIME type、大小。
- 檔案下載需檢查權限。
- Agent 寫出檔案的下載路徑必須限制在 `data/generated/{task_id}/`，不可有 path traversal。
- Agent runtime 必須強制 `max_iterations`、tool size limit、tool call 連錯上限。
- Tool result 在回灌 LLM 前必須截斷，避免 context 爆掉與敏感資料外洩。
- AI 輸出文件需包裝學術誠信提醒（由 tool 層自動附加）。
- AI 請求需要 timeout、retry 或錯誤處理。
- 不得把完整使用者檔案內容、LLM thinking 或完整 prompt 寫入不必要 logs。

---

### 3.5 Assignment Drafting Agent (Tool-calling)

#### Description
**這是本系統在運行時實際執行的 AI Agent**，不是設計階段的角色。每個任務啟動一個 Agent，透過 OpenAI-compatible API 的 tool calling 介面，多輪呼叫一組受控 tools，完成作業草稿生成。

#### Responsibilities
- 透過 `read_input_*` 讀取使用者上傳的課程資料與作業檔案。
- 拆解作業需求並用 `log_progress` 即時回報階段。
- 透過 `add_reference` 與 `add_limitation` 累積引用與限制。
- 透過 `write_text_file` / `write_docx_file` / `write_pdf_file` / `write_xlsx_file` 寫出交付檔案。
- 呼叫 `finish` 提供最終標題、作業摘要與講解，結束 loop。

#### Inputs
- `project.md` 的 AI-related Requirements 與 Tool-Use Boundary（§9）
- 任務 metadata（task_id、display_name、模型參數、迭代上限）
- 系統提示詞（後台設定，含學術誠信、tool use、繁體中文）
- 由後端注入的 tool catalog（依 Admin 啟停狀態過濾）
- Tool 執行結果（每輪回灌）

#### Outputs
- 一連串 AgentToolCall 紀錄
- 透過 tools 落地的 GeneratedFile / Reference / Limitation / ProgressEvent
- 最終 `finish(title, assignment_summary, explanation)`

#### Agent Behavior Rules
- 使用 `zh-TW` 台灣正體中文，不使用簡體字或大陸用語。
- 區分「根據上傳資料」、「Agent 推論 / 建議」、「待使用者確認」三類陳述。
- 不捏造引用；引用必須對應 `list_inputs` 中存在的檔案。
- 不協助規避偵測、不自動提交、不宣稱可直接交作業。
- 缺資料時 `add_limitation`，不要硬編內容。
- 至少要呼叫一次 `read_input_*`（如果有上傳檔案）再開始寫檔。
- 必須呼叫 `finish` 結束；不得依賴「停止呼叫工具」當作完成訊號。

#### Prompt Design Notes（給設計提示詞的人）
- 系統提示詞要明列 tools 清單與何時用、避免一次寫太大檔。
- 提示詞要附範例：何時用 DOCX 報告、何時用 XLSX 表格作業、何時只用 TXT 草稿。
- 提示詞要說明「`finish` 是唯一結束方法」與「達到迭代上限會被強制中止」。

---

### 3.6 File Processing Agent

#### Responsibilities
- 解析上傳檔案。
- 從 PDF、DOCX、TXT、MD、XLSX、CSV 擷取文字與表格。
- 產生檔案摘要。
- 將解析失敗狀態寫入 ProgressEvent。
- 保證解析失敗不會讓整個系統無法運作。

#### Inputs
- Uploaded files
- File metadata
- Task id

#### Outputs
- parsed_text
- parsed_table_json
- file_summary
- parse_status
- parse_error

#### Parsing Rules
- PDF: 使用 PyMuPDF 或同等工具擷取文字。
- DOCX: 使用 python-docx 擷取段落與表格。
- TXT / MD: 使用 UTF-8，必要時嘗試常見編碼 fallback。
- XLSX / CSV: 使用 pandas / openpyxl 擷取表格與欄位摘要。
- 若無法解析，記錄錯誤並讓任務繼續。
- 不得執行上傳檔案中的巨集或程式碼。

---

### 3.7 Tool Implementation Layer

#### Description
**這是 Agent 的工具實作層**，不是另一個 LLM Agent。負責把 Drafting Agent 的 tool call 轉成實際的副作用：讀檔、寫進度、寫 DOCX/PDF/XLSX、更新 DB。

#### Responsibilities
- 實作 §13 列出的每一個 tool。
- 對所有 tool 參數做 schema 驗證、size limit 檢查、檔名 sanitize。
- 確保副作用全部寫入沙箱 `data/generated/{task_id}/`。
- 在每次 tool 執行寫入 AgentToolCall 紀錄，無論成功失敗。
- 把成功的 write tool 結果寫成 GeneratedFile 並更新 ProgressEvent。
- 失敗時回傳結構化錯誤訊息給 Agent loop，由 Agent 自行決定要重試。

#### Inputs
- Agent 發出的 tool call（name + JSON arguments）
- 任務 metadata、上傳檔案解析結果
- Admin 設定（單檔大小、tool 啟停、檔案數上限）

#### Outputs
- 落地的 TXT / DOCX / PDF / XLSX
- GeneratedFile records
- Reference / Limitation records
- ProgressEvent records
- 截斷後的 tool result（回灌給 Agent）

#### Implementation Rules
- 每份 `write_*_file` 寫出的文件尾端必須統一附加：
  - 學術誠信提醒區塊
  - 人工確認清單（由 Agent 透過 add_limitation 累積 + 通用 boilerplate）
- 由 tool 層自動附加，不依賴 Agent 自行寫入，確保一致性。
- XLSX 非表格作業預設 sheets：`Summary` / `Answer` / `References` / `Checklist`，Agent 可覆寫。
- 單一 tool call 失敗不刪除任務已產出的其他檔案。
- 下載連結需檢查 session 與檔案歸屬。
- 任何時候都不能執行 Agent 提供的字串作為程式碼（不執行 shell、不 exec、不 eval、不執行 DOCX/PDF 內嵌巨集）。

---

### 3.8 QA Agent

#### Responsibilities
- 根據 acceptance criteria 測試功能。
- 找出 bug、edge cases、流程中斷點。
- 檢查資料、權限、錯誤狀態與安全性。
- 檢查 Demo 流程是否可順利展示。

#### Inputs
- `project.md`
- `agents.md`
- 完成的功能
- 測試環境
- Demo data

#### Outputs
- QA report
- Bug list
- Regression checklist
- Demo readiness report

#### QA Focus Areas
- Auth / permission
- File upload and parsing
- Assignment text validation
- AI API error handling
- Progress updates
- Detailed process view
- Document export
- History records
- Admin settings
- Security and privacy
- Academic integrity guardrails

---

### 3.9 DevOps / Deployment Agent

#### Responsibilities
- 設定部署流程。
- 管理環境變數。
- 檢查 build、hosting、domain、SSL、logging。
- 確保 staging / production 區分清楚。
- 提供本機 Demo 啟動文件。

#### Inputs
- 技術架構
- hosting requirements
- environment variables
- backend and frontend code

#### Outputs
- Dockerfile（frontend / backend）
- docker-compose.yml
- Deployment guide
- Environment setup
- Release checklist
- Demo startup guide
- Nginx Proxy Manager 設定說明

#### Required Environment Variables
- APP_SECRET_KEY
- SHARED_LOGIN_PASSWORD
- ADMIN_PASSWORD
- OPENAI_COMPATIBLE_BASE_URL
- OPENAI_COMPATIBLE_API_KEY
- OPENAI_COMPATIBLE_MODEL
- DATABASE_URL
- UPLOAD_DIR
- GENERATED_FILE_DIR
- MAX_FILE_SIZE_MB
- SESSION_EXPIRE_MINUTES

---

## 4. Execution Workflow

Agents must follow this workflow:

### Step 1: Read Documents

Before doing any work, every Agent must read:

1. `project.md`
2. `agents.md`
3. Any task-specific instruction from the user

### Step 2: Confirm Scope

Before implementation, the Agent must summarize:

- What it is about to build
- Which requirement it maps to
- What it will not include
- Any assumptions
- Any risk or ambiguity

### Step 3: Implement Incrementally

Implementation should be divided into small, testable units.

Each unit should include:

- Feature name
- Files changed
- Reason for change
- How to test
- Related acceptance criteria

### Step 4: Self-check

Before reporting completion, each Agent must verify:

- [ ] Feature matches `project.md`
- [ ] No out-of-scope features added
- [ ] Error states handled
- [ ] Empty states handled
- [ ] Loading states handled
- [ ] Permissions respected
- [ ] Basic tests passed
- [ ] No obvious security issue introduced
- [ ] API Key not exposed
- [ ] Academic integrity guardrails preserved

### Step 5: Report Completion

Each completion report must use this format:

```markdown
## Completion Report

### Task Completed
[任務名稱]

### Requirements Covered
- [project.md section]
- [acceptance criteria]

### Files Changed
- [file 1]
- [file 2]

### How to Test
1. [測試步驟 1]
2. [測試步驟 2]

### Known Limitations
- [限制 1]

### Follow-up Needed
- [後續事項 1]
```

---

## 5. Clarification Protocol

If an Agent encounters unclear requirements, it must not guess silently.

Use this format:

```markdown
## Clarification Needed

### Context
[目前正在處理什麼]

### Unclear Requirement
[不清楚的地方]

### Why This Matters
[為什麼會影響實作]

### Suggested Options
A. [選項 A]
B. [選項 B]
C. [選項 C]

### Recommended Default
[如果客戶沒有偏好，建議採用哪個選項與原因]
```

### Examples of Clarification Needed
- Google Login 是否必須納入 MVP？
- Demo 是否部署到公開網址？
- API Provider 是否固定為 OpenRouter？
- 是否需要 mock mode？
- 歷史紀錄需要保留多久？
- Admin 是否能查看完整學生輸出內容？
- PDF 是否需要固定版型？

---

## 6. Coding Standards

如果專案涉及程式碼，所有 Coding Agent 必須遵守：

- 程式碼要清楚、可維護、可擴充。
- 命名必須語意明確。
- 避免過度工程化。
- 不得硬編碼敏感資訊。
- 環境變數必須集中管理。
- 所有外部 API 錯誤必須被處理。
- 所有表單輸入必須驗證。
- 所有權限相關操作必須在後端再次驗證。
- UI 不得只依賴前端隱藏來保護資料。
- 重要操作需要 loading、success、error feedback。
- API response 格式需一致。
- 需避免重複程式碼。
- 需提供基本測試方式。

### 6.1 Suggested Backend Project Structure

```text
backend/
  app/
    main.py
    config.py
    database.py
    models/
      user.py
      task.py
      uploaded_file.py
      progress_event.py
      generated_file.py
      system_setting.py
      system_setting_history.py
    routers/
      auth.py
      tasks.py
      files.py
      history.py
      admin.py
    services/
      auth_service.py
      file_parser_service.py
      agent_runtime.py        # 跑 Agent loop（chat + tool dispatch + 上限）
      progress_service.py
      history_service.py
      system_setting_service.py
    tools/                    # Agent tool 實作層（§13 列出的每個 tool 一個 module）
      __init__.py
      registry.py             # 依 Admin 設定組 tool catalog
      read_inputs.py          # list_inputs / read_input_text / read_input_table
      annotate.py             # log_progress / add_reference / add_limitation
      write_files.py          # write_text_file / write_docx_file / write_pdf_file / write_xlsx_file
      finish.py
    utils/
      security.py
      validators.py
      file_utils.py
  tests/
  requirements.txt
  .env.example
```

### 6.2 Suggested Frontend Project Structure

```text
frontend/
  src/
    main.tsx
    App.tsx
    api/
      client.ts
      auth.ts
      tasks.ts
      admin.ts
    components/
      StudentLoginForm.tsx
      AdminLoginForm.tsx
      CourseMaterialUploader.tsx
      AssignmentUploader.tsx
      OutputFormatSelector.tsx
      ProgressPanel.tsx
      DetailedProcessPanel.tsx
      ResultViewer.tsx
      DownloadLinks.tsx
      AdminSettingsForm.tsx
    pages/
      StudentLoginPage.tsx
      AdminLoginPage.tsx
      MainAppPage.tsx
      HistoryPage.tsx
      AdminSettingsPage.tsx
    types/
      task.ts
      settings.ts
    utils/
      fileValidation.ts
      formatters.ts
  package.json
  .env.example
```

---

## 7. Security & Privacy Rules

Agents must:

- 保護使用者個資。
- 不在前端暴露 secret keys。
- 不記錄敏感資料到 console 或 logs。
- 檢查使用者是否有權限存取該資料。
- 對所有使用者輸入做驗證。
- 避免 SQL injection、XSS、CSRF 等常見問題。
- 若涉及付款、醫療、金融、法律或未成年人，必須提高審查標準。
- 上傳檔案必須檢查大小、格式與 MIME type。
- 下載檔案必須檢查 session 與檔案歸屬。
- Admin 設定不得回傳完整 API Key。
- 任務紀錄應提供刪除或清除機制。

### 7.1 Sensitive Data Handling
不得在以下位置存放完整敏感資料：

- frontend source code
- browser localStorage
- browser console
- public logs
- generated output files
- Git repository
- screenshots used for demo

### 7.2 File Upload Safety
- 不執行使用者上傳檔案中的任何程式碼。
- 不執行 Office macro。
- 僅解析文字與表格內容。
- 不信任副檔名，後端需再次檢查 MIME type。
- 檔案存放路徑不可直接由使用者控制。

---

## 8. AI Agent Behavior Rules

如果專案本身包含 AI Agent，該 AI Agent 必須遵守以下規則：

### 8.1 Role Boundaries

AI Agent 只能執行 `project.md` 定義的任務，不得自行扮演未授權角色。

AI Agent 可以：
- 整理講義重點。
- 拆解作業需求。
- 產生作業草稿。
- 產生回答架構。
- 產生學習建議。
- 產生引用來源摘要。
- 產生人工確認清單。

AI Agent 不可以：
- 協助自動提交作業。
- 協助繞過學校規範。
- 協助規避 AI 偵測或抄襲偵測。
- 聲稱輸出可以直接提交。
- 捏造不存在的來源或引用。

### 8.2 Input Handling

AI Agent must:

- 明確理解使用者輸入。
- 不確定時提出澄清問題或列出假設。
- 對缺漏資訊做標註。
- 不捏造不存在的資料。
- 對上傳資料與 AI 推論做區隔。
- 對表格、數據、程式碼與引用要求使用者人工確認。

### 8.3 Output Format

AI Agent 的輸出必須：

- 結構化。
- 可讀。
- 可操作。
- 符合指定格式。
- 清楚區分事實、假設與建議。
- 包含學術誠信提醒。
- 包含人工確認清單。
- 包含資料來源摘要。
- 不包含完整內部 chain-of-thought。

### 8.4 Memory / Context Rules

如需記憶使用者資訊，必須定義：

- 可以記憶什麼：
  - 任務 id
  - 使用者選擇的輸出格式
  - 上傳檔案 metadata
  - 生成結果
  - 任務狀態
- 不可以記憶什麼：
  - 明文密碼
  - API Key
  - 不必要的敏感個資
  - 無管理目的的完整私人作業內容
- 何時需要使用者同意：
  - 保存任務歷史
  - 保存上傳檔案
  - 使用任務資料作為 Demo 範例
- 如何更新或刪除記憶：
  - 使用者可刪除自己的任務紀錄。
  - Admin 可設定任務保留天數。
  - 過期檔案可自動清理。

### 8.5 Failure Handling

當 AI Agent 無法完成任務時，必須回覆：

```markdown
## Unable to Complete

### Reason
[無法完成原因]

### Missing Information
[缺少什麼]

### Suggested Next Step
[建議下一步]
```

### 8.6 Tool Use Rules

當 AI Agent 透過 tool calling 操作系統時：

- 只能呼叫後端在當輪 catalog 中提供的 tools；不得呼叫未列出的 tool name。
- 不得把 API Key、密碼、其他使用者資料當作 tool 參數。
- 寫檔前應先 `read_input_*` 至少一次（若有上傳檔案），避免幻想內容。
- 同一檔名重寫表示「我要修正前一版」，新版會覆蓋舊版，請謹慎使用。
- 達到迭代上限前必須呼叫 `finish`；若還沒準備好，先 `add_limitation` 說明，再 `finish`，比靜默超時好。
- Tool 失敗時讀錯誤訊息並調整參數重試；連續同一 tool 失敗 3 次以上應改換策略或 `add_limitation` 後 `finish`。
- 不得在 tool arguments 中夾帶試圖讓 tool 層執行任意程式碼的字串（例如 shell 命令、SQL）；tool 層會做 sanitize，但 Agent 也要主動避免。

### 8.7 Refusal Handling

當使用者要求不當用途時，AI Agent 必須回覆：

```markdown
## 無法協助此要求

### 原因
此要求可能涉及違反學術誠信、規避偵測或直接代替使用者完成可提交作業。

### 我可以改為協助
- 拆解作業要求
- 產生回答大綱
- 解釋相關概念
- 產生草稿供你自行修改
- 建立檢查清單
```

---

## 9. QA Checklist for Agents

每次 Agent 完成任務後，QA Agent 或執行 Agent 必須檢查：

- [ ] 是否符合 `project.md` 的功能範圍
- [ ] 是否符合 `agents.md` 的工作規則
- [ ] 是否處理主要使用流程
- [ ] 是否處理 edge cases
- [ ] 是否處理 loading / empty / error states
- [ ] 是否符合角色權限
- [ ] 是否沒有暴露敏感資訊
- [ ] 是否有基本測試方式
- [ ] 是否有明確完成回報
- [ ] 是否保留學術誠信提醒
- [ ] 是否避免協助規避偵測或自動提交
- [ ] 是否在後端驗證權限
- [ ] 是否處理 AI API 錯誤
- [ ] 是否處理檔案解析失敗
- [ ] 是否處理文件輸出失敗
- [ ] 是否確保下載連結權限檢查

---

## 10. Change Management

如果客戶提出新需求，Agent 必須先判斷：

1. 這是 bug fix 嗎？
2. 這是 MVP 原本範圍嗎？
3. 這是 scope change 嗎？
4. 是否會影響資料模型、API、UI、時程或成本？
5. 是否涉及學術誠信、安全或隱私風險？

若是 scope change，必須使用以下格式回報：

```markdown
## Scope Change Detected

### Requested Change
[新需求]

### Impacted Areas
- [影響區域 1]
- [影響區域 2]

### Impact Level
Low / Medium / High

### Risk Review
- Academic Integrity Risk: Low / Medium / High
- Security Risk: Low / Medium / High
- Privacy Risk: Low / Medium / High

### Recommendation
[建議是否納入，以及納入哪個階段]

### Required Document Updates
- [ ] Update project.md
- [ ] Update agents.md if needed
- [ ] Update acceptance criteria
```

---

## 11. Release Checklist

正式交付前必須確認：

- [ ] MVP features completed
- [ ] Core user journeys tested
- [ ] Admin flows tested
- [ ] Auth and permissions tested
- [ ] Data creation / update / deletion tested
- [ ] Error states tested
- [ ] Empty states tested
- [ ] Responsive layout tested
- [ ] Environment variables configured
- [ ] Deployment successful or local demo startup verified
- [ ] No secret keys exposed
- [ ] Basic analytics configured, if applicable
- [ ] Client acceptance criteria reviewed
- [ ] Demo data prepared
- [ ] API provider tested
- [ ] Mock mode prepared, if needed
- [ ] Academic integrity notice visible
- [ ] AI output includes human review checklist
- [ ] File download permission checked
- [ ] History records tested
- [ ] Admin settings tested

---

## 12. Demo Preparation Guide

### 12.1 Required Demo Materials
- 一份 PDF 講義範例。
- 一份 DOCX 或 TXT 作業題目範例。
- 一份 XLSX 或 CSV 資料分析範例。
- 一段手動輸入作業敘述。
- 一組測試密碼。
- 一組測試 API 設定。
- 一份預期輸出展示。

### 12.2 Recommended Demo Flow
1. 開啟學生登入頁。
2. 輸入學生共用密碼登入。
3. 展示主頁左右分欄。
4. 左側上傳課程資料。
5. 右側上傳作業檔案並輸入作業敘述。
6. 選擇純文字、DOCX、PDF。
7. 勾選學術誠信確認。
8. 按下開始生成。
9. 展示即時進度。
10. 點開詳細過程。
11. 展示 AI 結果。
12. 下載文件。
13. 進入歷史紀錄查看剛剛任務。
14. 登出學生帳號，開啟 Admin 登入頁。
15. 輸入管理者密碼登入。
16. 進入 Admin 頁展示 API 設定，不顯示完整 API Key。

### 12.3 Demo Backup Plan
- 若 API 失敗，啟用 mock result。
- 若 PDF 產生失敗，展示 DOCX 與純文字。
- 若上傳解析失敗，使用 TXT / MD 備用資料。
- 若網路不穩，使用本機 localhost Demo。

---

## 13. Agent Tool Catalog

本節定義 Assignment Drafting Agent 可呼叫的所有 tool。所有 tool 都在後端 sandbox 內執行，輸入經過 schema 驗證，輸出可能被截斷後回灌 LLM。

### 13.1 Read Tools

#### `list_inputs`
- **Purpose**: 列出本任務所有上傳檔案。
- **Arguments**: 無。
- **Returns**:
  ```json
  {
    "files": [
      {
        "file_id": "uuid",
        "category": "course_material | assignment_file",
        "filename": "string",
        "file_type": "pdf | docx | txt | md | xlsx | csv | png | jpg | webp | unknown",
        "size_bytes": 12345,
        "parse_status": "success | failed | skipped",
        "summary": "string (前 300 字摘要)"
      }
    ]
  }
  ```

#### `read_input_text`
- **Purpose**: 讀取某個檔案的解析文字內容。
- **Arguments**:
  ```json
  { "file_id": "uuid", "max_chars": 4000 }
  ```
- **Returns**:
  ```json
  {
    "file_id": "uuid",
    "filename": "string",
    "text": "string (依 max_chars 截斷，預設 4000，上限 8000)",
    "truncated": true
  }
  ```
- **Errors**: `file_not_found`、`not_parsed`、`unsupported_for_text`。

#### `read_input_table`
- **Purpose**: 讀取已解析的表格資料。
- **Arguments**: `{ "file_id": "uuid", "sheet": "string (optional)" }`
- **Returns**: `{ "sheets": [{ "name": "string", "columns": ["..."], "rows": [[...], ...], "row_count": int, "truncated": bool }] }`
- **Limits**: 單次最多回傳 200 列 × 30 欄；超出時截斷並回 `truncated=true`。

### 13.2 Annotate Tools

#### `log_progress`
- **Purpose**: 寫一筆 ProgressEvent 推送給前端。
- **Arguments**: `{ "stage": "string (e.g. analyzing | drafting | writing_docx)", "message": "string (<= 200 字)" }`
- **Returns**: `{ "event_id": "uuid" }`

#### `add_reference`
- **Purpose**: 累積一條引用來源。
- **Arguments**: `{ "source_name": "string", "quote_or_summary": "string (<= 500 字)", "used_for": "string (<= 200 字)" }`
- **Returns**: `{ "reference_id": "uuid" }`
- **Rule**: `source_name` 必須對應 `list_inputs` 中存在的檔名，或標明為「Agent 知識」。

#### `add_limitation`
- **Purpose**: 累積一條限制 / 缺資料說明。
- **Arguments**: `{ "text": "string (<= 300 字)" }`
- **Returns**: `{ "limitation_id": "uuid" }`

### 13.3 Write Tools

所有 write tool 共同規則：
- `filename` 由後端 sanitize：禁止 `..`、`/`、`\`、絕對路徑，限制 100 字元，副檔名必須符合白名單。
- 同名再次寫入會覆蓋，並寫一筆新的 AgentToolCall（舊檔案不再保留）。
- 每個檔案大小上限預設 10MB（由 Admin 設定）。
- 單任務總檔案數上限預設 8（由 Admin 設定）。
- Tool 層會在文件尾端自動附加學術誠信提醒區塊。

#### `write_text_file`
- **Purpose**: 寫出 TXT 或 MD。
- **Arguments**:
  ```json
  {
    "filename": "string (副檔名 .txt 或 .md)",
    "purpose": "string (<= 200 字)",
    "content": "string (<= 30000 字)"
  }
  ```
- **Returns**: `{ "generated_file_id": "uuid", "filename": "...", "size_bytes": int }`

#### `write_docx_file`
- **Purpose**: 寫出 DOCX。Agent 提供結構化 blocks，tool 層用 python-docx 組裝。
- **Arguments**:
  ```json
  {
    "filename": "string (.docx)",
    "purpose": "string",
    "blocks": [
      { "type": "heading", "level": 1, "text": "string" },
      { "type": "paragraph", "text": "string" },
      { "type": "bullet_list", "items": ["string", "..."] },
      { "type": "numbered_list", "items": ["string", "..."] },
      { "type": "table", "columns": ["..."], "rows": [["...", "..."], ...] }
    ]
  }
  ```
- **Limits**: `blocks` 上限 200；單一 text 上限 2000 字；單一 table 上限 100 列 × 20 欄。
- **Returns**: `{ "generated_file_id": "uuid", "filename": "...", "size_bytes": int }`

#### `write_pdf_file`
- **Purpose**: 寫出 PDF。Arguments / blocks 結構同 `write_docx_file`。
- **Implementation**: tool 層用 ReportLab 或 WeasyPrint。
- **Returns**: 同上。

#### `write_xlsx_file`
- **Purpose**: 寫出 XLSX，多 sheet。
- **Arguments**:
  ```json
  {
    "filename": "string (.xlsx)",
    "purpose": "string",
    "sheets": [
      {
        "name": "string (<= 30 字)",
        "columns": ["string", "..."],
        "rows": [["..."], ["..."]]
      }
    ]
  }
  ```
- **Limits**: 單檔最多 10 sheets；每個 sheet 上限 500 列 × 30 欄。
- **Returns**: 同 `write_docx_file`。

### 13.4 End Tool

#### `finish`
- **Purpose**: 結束 Agent loop，提供最終總結。
- **Arguments**:
  ```json
  {
    "title": "string (<= 100 字)",
    "assignment_summary": "string (<= 500 字)",
    "explanation": "string (<= 3000 字)"
  }
  ```
- **Returns**: `{ "ok": true }`
- **Side effects**: 將值寫入 Task 的 `agent_title` / `agent_assignment_summary` / `agent_explanation`，任務狀態設為 `completed`。
- **Rule**: `finish` 之後的任何 tool call 一律標記 `ignored`，不執行。

### 13.5 Error Schema

所有 tool 失敗時回傳：
```json
{
  "error": {
    "code": "string (e.g. invalid_argument | file_not_found | size_limit_exceeded | tool_disabled)",
    "message": "string (人類可讀，給 LLM 看)",
    "details": { }
  }
}
```

---

## 14. Agent Execution Loop

### 14.1 Loop Skeleton

```text
messages = [
  { role: "system",  content: system_prompt },
  { role: "user",    content: build_user_prompt(task) }
]
for iteration in 1..max_iterations:
  response = llm.chat(
    model=model_name,
    messages=messages,
    tools=enabled_tools,
    tool_choice="auto"
  )
  if response.tool_calls is empty:
    # Agent 嘗試只用文字回應 → 強制提醒它要呼叫 finish
    messages.append(reminder_message_to_use_finish)
    continue

  for call in response.tool_calls:
    record = create_agent_tool_call(task, iteration, call)
    result_or_error = dispatch_tool(call)
    persist_side_effects(result_or_error)
    finalize_agent_tool_call(record, result_or_error)
    messages.append({ role: "tool", tool_call_id: call.id, content: truncate(result_or_error) })
    if call.name == "finish":
      mark_task_completed(task)
      return

mark_task_failed(task, reason="max_iterations_reached")
```

### 14.2 Lifecycle

1. **準備**：解析所有 UploadedFile（若還沒），組 system prompt + user prompt + tool catalog（只放啟用的 tools）。
2. **執行**：上面的 loop。
3. **收尾**：若狀態為 `completed`，回傳前端 task 詳情；若為 `failed`（含達上限），仍保留已寫出的 GeneratedFile、Reference、Limitation。

### 14.3 Safety Caps

| Cap | 預設 | 由誰設定 |
|---|---|---|
| `max_iterations` | 20 | Admin |
| 單檔大小 | 10 MB | Admin |
| 單任務檔案數 | 8 | Admin |
| 單次 tool result 回灌 | 4000 字（截斷） | 程式碼常數 |
| Tool call 連續錯誤 | 同一 tool 連錯 5 次 → 強制 `finish` | 程式碼常數 |

### 14.4 Observability

- 每次 LLM call 紀錄 `iteration`、`prompt_tokens`、`completion_tokens`、`elapsed_ms`（不存完整 prompt 內容到 DB，避免敏感資料外洩）。
- 每個 tool call 寫一筆 AgentToolCall（含截斷後的 arguments / result）。
- ProgressEvent 由 `log_progress` 與 tool 層自動產生（例如「Agent 寫入 xxx.docx」）。
- 詳細過程 API 回傳：ProgressEvent + AgentToolCall + Reference + Limitation + GeneratedFile。

### 14.5 Failure Modes

| 情境 | 處理 |
|---|---|
| LLM 連線失敗 | 重試 2 次（指數退避），仍失敗則 `failed`，寫 error ProgressEvent |
| LLM 回傳格式錯誤的 tool call | 寫 AgentToolCall 為 `error`，把錯誤訊息回灌 LLM，繼續下一輪 |
| Tool 內部例外 | 同上，回 `error` 給 LLM |
| 達 `max_iterations` 仍未 `finish` | `failed`，保留已寫檔，前端顯示「Agent 未能完成，請重試或縮小範圍」 |
| LLM 一直回純文字不呼叫工具 | 連續 3 輪純文字 → 加 reminder 提示要用 tools；連 5 輪仍如此 → `failed` |
