# project.md

## 1. Project Overview

### 1.1 Project Name
AI 課業輔助與作業草稿生成系統

### 1.2 One-line Description
一個以 Python FastAPI 為後端、串接 OpenAI-compatible API 的期末專題 Web 系統。使用者上傳課程資料與作業需求後，後端啟動一個 **AI Agent**，由 Agent 透過一組「檔案操作 tools」自行讀取輸入、規劃輸出、寫出可下載交付檔案，並產生講解內容回傳給使用者。

### 1.3 Background / Problem
學生在處理期末報告、程式作業、數據分析作業、閱讀心得或混合型作業時，通常需要同時整理講義、理解作業要求、規劃回答架構、產生初稿、轉換輸出格式。本專案希望展示一個 AI 輔助型網頁系統，讓使用者能集中上傳課程資料與作業需求，並由 AI 產生結構化草稿、解題輔助、引用來源與可下載文件。

本專案定位為小範圍課程實驗 Demo，用來展示檔案上傳、圖片判讀、AI 內容生成、文件輸出與下載流程；系統不自動送交外部平台。

### 1.4 Business / Product Goals
- 完成一個可在期末專題中展示的 AI Web App Demo。
- 展示 Python 後端、前端介面、檔案解析、AI API 串接、即時進度、文件輸出等整合能力。
- 展示 **LLM Tool Use / Agent Loop** 的設計：AI 不再只是「一次回應」，而是會「呼叫工具讀資料、寫檔案、回報進度」的 Agent。
- 支援使用者上傳課程資料與作業需求，由 Agent 產生結構化作業草稿或解題輔助內容。
- 支援 PDF、Word、Excel、純文字等多格式輸出，全部由 Agent 透過 tools 直接寫出。
- 提供可檢視的處理流程：tool call 紀錄、來源引用、限制說明與最終交付檔案。

### 1.5 Success Metrics
- 使用者能在通過驗證後成功進入主系統。
- 使用者能成功上傳課程資料與作業檔案，不以副檔名或 MIME type 限制格式。
- 使用者能手動輸入作業敘述並送出任務。
- 系統能啟動 AI Agent，Agent 能透過 tool calling 完成多輪推理。
- 系統能即時顯示 Agent 的 tool call 與處理階段。
- 系統能成功呼叫 OpenAI-compatible API（含 tool calling 模式）並回傳結果。
- Agent 能透過 tools 直接寫出 PDF、DOCX、TXT 或 XLSX 檔案到任務工作目錄。
- 系統能在 Demo 情境中穩定完成至少 3 種作業類型測試。
- 系統輸出包含 AI 講解、引用來源、限制說明與 Agent 產出的下載檔案。

---

## 2. Target Users & Roles

### 2.1 User Personas

#### Persona 1: Student User
- Description: 使用系統的學生，可能需要整理講義、理解作業題目、產生報告草稿、產生資料分析說明或取得作業輔助內容。
- Goals:
  - 快速整理上傳資料中的重點。
  - 根據作業要求產生可修改的草稿。
  - 取得引用來源與處理流程。
  - 下載 PDF、Word、Excel 或純文字結果。
- Pain Points:
  - 作業要求分散在講義、PDF、舊作業與文字說明中。
  - 不知道如何開始規劃回答架構。
  - 需要花時間整理格式與輸出文件。
- Main Actions:
  - 登入系統。
  - 上傳課程資料。
  - 上傳作業檔案。
  - 輸入作業敘述。
  - 查看 AI 決定的輸出檔案。
  - 查看處理進度。
  - 查看詳細過程。
  - 下載或複製結果。

#### Persona 2: Demo Evaluator / Teacher
- Description: 評分老師或專題展示觀眾，用來檢查系統功能完整性與技術整合能力。
- Goals:
  - 看到系統從輸入到輸出的完整流程。
  - 確認 AI 串接與文件輸出可正常運作。
  - 確認系統不會自動送交外部平台。
- Pain Points:
  - 若系統只是簡單呼叫 AI，專題深度不足。
  - 若系統看不到處理過程，難以評估技術含量。
- Main Actions:
  - 使用測試密碼或測試帳號登入。
  - 使用範例檔案測試流程。
  - 檢查輸出文件與處理紀錄。

#### Persona 3: Admin User
- Description: 系統管理者或專題開發者，用來設定 API endpoint、模型、系統提示詞、密碼、輸出格式與任務紀錄。
- Goals:
  - 管理 API 設定。
  - 查看任務紀錄。
  - 管理系統參數。
  - 控制可用輸出格式與檔案大小限制。
- Pain Points:
  - API Key 不可暴露在前端。
  - 不同模型和 endpoint 的相容性需要管理。
- Main Actions:
  - 登入後台。
  - 更新模型設定。
  - 查看任務歷史。
  - 匯出或刪除紀錄。

### 2.2 User Roles & Permissions

| Role | Can Do | Cannot Do | Notes |
|---|---|---|---|
| Guest | 查看登入頁、輸入密碼或登入帳號 | 使用主系統、查看任務紀錄、存取檔案 | 未驗證前不可進入系統 |
| Student User | 上傳檔案、輸入作業敘述、建立 AI 任務、查看自己的任務結果與下載檔案 | 修改系統 API 設定、查看其他使用者任務 | MVP 可用共用密碼；正式版使用 OAuth / 帳號登入 |
| Admin User | 管理 API endpoint、模型名稱、系統提示詞、檔案限制、任務紀錄 | 直接查看不屬於管理目的的敏感內容 | 後台操作需更高權限 |
| Demo Evaluator | 使用測試資料體驗完整流程 | 修改 API Key 或刪除資料 | 可使用測試帳號或測試密碼 |

---

## 3. Scope Definition

### 3.1 MVP Scope
第一版必須完成的功能：

- 密碼驗證或簡化登入頁。
- 主系統頁面採左右分欄：
  - 左側：課程相關資料上傳區，可選。
  - 右側：作業檔案上傳區與作業敘述文字輸入區，至少提供一項，也可同時提供。
- 上傳檔案不限制格式；PDF、DOCX、TXT、MD、XLSX、CSV、PNG、JPG、WEBP 會嘗試解析，其他格式保留 metadata。
- 支援輸出格式：PDF、DOCX、XLSX、純文字顯示，全部由 Agent 透過 tools 寫出。
- 串接 OpenAI-compatible API（含 tool calling），預設支援可自訂 base URL、API Key、model name。
- **AI Agent Loop**：後端為每個任務啟動一個 Agent，Agent 自行決定多輪呼叫 tools，直到呼叫 `finish` 或達到上限。
- 顯示即時處理進度（包含 Agent 的 tool call 訊息）。
- 顯示詳細處理過程頁籤或展開區塊（tool trace、引用、限制）。
- 完成後顯示 AI 講解、複製按鈕與 Agent 寫出檔案的下載連結。
- 儲存歷史紀錄，包括任務輸入摘要、Agent 講解、tool call 紀錄、檔案下載路徑與建立時間。
- 管理後台，可設定 API endpoint、模型名稱、系統提示詞、Agent 迭代上限與檔案大小限制。
- 基本錯誤處理與防呆提示。

### 3.2 Out of Scope
第一版明確不做的事項：

- 自動登入學校 LMS 或替使用者提交作業。
- 繞過抄襲偵測、規避 AI 偵測或隱藏 AI 使用痕跡。
- 保證答案正確或保證符合任課老師評分標準。
- 複雜多租戶 SaaS 權限系統。
- 付款功能。
- 手機 App。
- 即時多人協作編輯。
- 對大型影片、音訊或掃描 PDF 進行完整解析。
- 使用者之間共享作業結果。

### 3.3 Future Scope
後續版本可考慮的功能：

- Google Login 或學校 SSO 登入。
- 使用者分級與管理員邀請機制。
- 任務歷史搜尋、篩選與標籤。
- RAG 向量檢索，支援大量課程資料。
- 掃描檔 OCR。
- 更多輸出模板，例如報告格式、簡報大綱、研究摘要、程式碼說明。
- 引用格式選擇，例如 APA、MLA、IEEE。
- 作業自我評分 rubric。
- 系統使用統計 Dashboard。
- 批次處理多份作業或多份講義。

---

## 4. Core User Journeys

### Journey 1: 使用者登入系統

#### User Story
As a Guest, I want to enter a password or login credential, so that I can access the AI assignment assistant securely.

#### Flow
1. 使用者進入網站。
2. 學生進入學生登入頁（`/login`），Admin 進入管理者登入頁（`/admin/login`）。
3. 學生輸入暱稱與共用密碼，系統驗證密碼後以暱稱建立帶有唯一識別的 session/cookie，同暱稱可關聯歷史紀錄。
4. Admin 輸入管理者密碼，系統驗證後建立 Admin session。
5. 使用者進入對應系統頁面（學生進入主系統，Admin 進入後台）。

#### Edge Cases
- 密碼錯誤。
- session 過期。
- 使用者嘗試直接存取主頁 URL。
- 學生嘗試存取 Admin 頁面。

#### Acceptance Criteria
- [ ] 未登入者無法存取主系統頁面。
- [ ] 密碼錯誤時顯示明確錯誤訊息。
- [ ] 登入成功後能進入主系統。
- [ ] 登出後不可透過瀏覽器返回鍵繼續操作。

---

### Journey 2: 建立 AI 課業輔助任務

#### User Story
As a Student User, I want to upload course materials and assignment requirements, so that the AI can generate a structured draft with references.

#### Flow
1. 使用者進入主系統。
2. 左側上傳課程資料，可選。
3. 右側上傳作業檔案、在文字框輸入作業敘述，至少提供一項，也可同時提供。
4. 使用者按下「開始生成」。
5. 系統建立任務紀錄（Task）。
6. 系統將使用者已選擇的檔案上傳至後端，關聯至該 Task。
7. 系統進入檔案解析、需求分析、內容生成、格式輸出流程。

#### Edge Cases
- 使用者未提供作業檔案與作業敘述。
- 使用者同時提供作業檔案與作業敘述。
- 使用者未上傳任何檔案，但有輸入文字。
- 檔案無法解析內容，只能保留 metadata。
- 檔案大小超過限制。
- 上傳檔案解析失敗。
- API Key 錯誤。
- API timeout。

#### Acceptance Criteria
- [ ] 使用者需要提供作業檔案或作業敘述至少一項才可送出。
- [ ] 系統支援無課程資料但有文字作業敘述的情境。
- [ ] 系統不因格式拒絕檔案；無法解析的格式會保留檔名、格式與大小。
- [ ] 任務建立後會顯示進度。
- [ ] 任務完成後會顯示結果與下載連結。

---

### Journey 3: 查看即時進度與詳細過程

#### User Story
As a Student User, I want to see what the system is doing, so that I can understand how the output was generated.

#### Flow
1. 使用者按下生成按鈕。
2. 前端開啟進度區塊。
3. 系統逐步顯示狀態：
   - 任務建立中
   - 檔案上傳完成
   - 檔案解析中
   - Agent 啟動
   - Agent tool call（例如：`list_inputs`、`read_input_text`、`log_progress`、`write_docx_file` 等，逐筆即時推送）
   - Agent 呼叫 `finish` → 任務完成
4. 使用者可點擊「查看詳細過程」。
5. 系統顯示可公開的處理紀錄：
   - 已解析檔案清單
   - 每份檔案擷取到的文字摘要
   - Agent 的 tool call trace（tool 名稱、輸入摘要、回傳摘要、時間戳）
   - Agent 透過 `add_reference` 累積的引用來源
   - Agent 透過 `add_limitation` 累積的限制說明
   - Agent 已寫出檔案清單
   - 系統警告或錯誤

#### Edge Cases
- SSE 連線中斷。
- 使用者重新整理頁面。
- 後端任務仍在執行但前端斷線。
- 任務失敗。

#### Acceptance Criteria
- [ ] 使用者可看到即時進度文字（包含 Agent 每次 tool call 的階段訊息）。
- [ ] 使用者可展開詳細過程，看到 tool call trace 與引用、限制清單。
- [ ] 詳細過程不得顯示 API Key、系統敏感設定或 Agent 的完整 chain-of-thought（thinking）內容。
- [ ] 若 Agent 失敗或達到迭代上限，系統顯示失敗階段與可重試建議。

---

### Journey 4: 取得輸出結果

#### User Story
As a Student User, I want to download or copy the AI-generated result, so that I can review, edit, and use it as a learning draft.

#### Flow
1. 任務完成（Agent 呼叫 `finish`）後，系統顯示 AI 講解結果。
2. 系統列出 Agent 在執行期間透過 tools 寫出的所有檔案（每筆包含 filename、format、purpose、下載連結）。
3. 使用者可逐筆下載 PDF、DOCX、TXT、XLSX 等檔案。

#### Edge Cases
- 文件產生失敗但文字結果成功。
- 下載連結過期或檔案不存在。
- Excel 輸出不適合非表格型內容。

#### Acceptance Criteria
- [ ] 使用者能複製 Agent 的純文字講解。
- [ ] 使用者能下載 Agent 透過 tools 寫出的每一份檔案。
- [ ] 文件內容需與 Agent 呼叫 `write_*_file` 時提供的內容一致。
- [ ] 若某個 tool call 失敗（例如 PDF 寫入失敗），不影響其他已成功寫出的檔案與 Agent 的純文字講解。

---

### Journey 5: 管理者設定系統

#### User Story
As an Admin User, I want to configure API and system settings, so that the application can use different OpenAI-compatible providers safely.

#### Flow
1. 管理者登入後台。
2. 管理者查看目前 API 設定。
3. 管理者修改 base URL、model name、temperature、max tokens、系統提示詞。
4. 管理者設定支援檔案大小與輸出格式。
5. 管理者儲存設定。
6. 系統使用新設定處理後續任務。

#### Edge Cases
- API Key 格式錯誤。
- base URL 無法連線。
- model name 不存在。
- 使用者輸入過長系統提示詞。

#### Acceptance Criteria
- [ ] API Key 不會顯示完整明文。
- [ ] 後台設定只有 Admin 可存取。
- [ ] 設定修改後會記錄 updated_at。
- [ ] 系統能用測試請求驗證 API 設定是否可用。

---

## 5. Feature Requirements

### Feature 1: Authentication Gate

#### Description
系統有兩個獨立登入頁面：學生登入頁與管理者登入頁。學生輸入暱稱與共用密碼登入，系統以暱稱作為使用者識別，用於歷史紀錄與檔案歸屬（同暱稱可看到之前的任務紀錄）。Admin 使用獨立的管理者密碼登入。正式版可擴充 Google Login 或學校 SSO。

#### User Roles
- Guest
- Student User
- Admin User

#### Functional Requirements
- 學生登入頁：輸入暱稱與共用密碼（SHARED_LOGIN_PASSWORD），驗證密碼後以暱稱建立使用者識別與 session/cookie。同暱稱登入可關聯歷史紀錄。
- Admin 登入頁：輸入管理者密碼（ADMIN_PASSWORD），驗證後建立 Admin session。
- 兩個登入頁為獨立路由（例如 `/login` 與 `/admin/login`）。
- 密碼從環境變數讀取，不可硬編碼在前端。
- 每個學生 session 具有唯一 session_id，並以暱稱（display_name）作為使用者識別，用於關聯歷史紀錄與檔案歸屬。
- 登入成功建立 session。
- 支援登出。
- 後台路由需額外檢查 Admin 權限。

#### UI Requirements
- 學生登入頁：暱稱輸入框、密碼輸入框、登入按鈕、錯誤訊息區。
- Admin 登入頁：密碼輸入框、登入按鈕、錯誤訊息區。
- 可選：Google Login 按鈕，若未設定則隱藏（Future Scope）。

#### Data Requirements
- session_id
- user_id or anonymous_user_id
- display_name（學生暱稱）
- role
- login_time
- session_expire_time

#### Business Rules
- 未登入不可進入主頁。
- Admin 頁面不可只靠前端隱藏，後端也必須檢查。
- 密碼錯誤不可顯示系統細節。

#### Error / Empty States
- 密碼錯誤：顯示「密碼錯誤，請重新輸入」。
- session 過期：顯示「登入已過期，請重新登入」。

#### Acceptance Criteria
- [ ] 未登入直接打開 `/app` 會被導回登入頁。
- [ ] 成功登入後可進入主系統。
- [ ] 登出後 session 失效。

---

### Feature 2: Course Material Upload

#### Description
左側區塊允許使用者上傳課程相關資料，例如講義、以前作業、課程筆記、CSV/XLSX 資料。

#### User Roles
- Student User

#### Functional Requirements
- 支援多檔上傳。
- 不限制檔案格式；PDF、DOCX、TXT、MD、XLSX、CSV、PNG、JPG、WEBP 會嘗試解析，其他格式保留 metadata。
- 顯示每個檔案名稱、大小、狀態。
- 可移除已選檔案。
- 檔案為可選，不是必填。
- 上傳後後端解析文字與表格內容。

#### UI Requirements
- 左側標題：「課程資料，可選」。
- 拖放上傳區。
- 點選上傳區後支援 `Ctrl+V` 貼上剪貼簿檔案或圖片。
- 檔案清單。
- 上傳格式與大小限制說明。

#### Data Requirements
- file_id
- task_id
- original_filename
- stored_filename
- file_type
- file_size
- parsed_text
- parsed_table_json
- parse_status
- created_at

#### Business Rules
- 不因格式拒絕送出；未知格式不得執行內容，只保留 metadata。
- 單檔大小限制預設 10MB，可由 Admin 調整。
- 檔案解析失敗不一定中止整個任務，但需顯示警告。

#### Error / Empty States
- 未上傳：顯示「未提供課程資料，AI 將只根據作業需求生成」。
- 解析失敗：顯示「此檔案無法解析，已略過」。

#### Acceptance Criteria
- [ ] 使用者能上傳任意格式檔案。
- [ ] 系統能顯示上傳檔案清單。
- [ ] 未知格式會保留 metadata，不會因格式被拒絕。
- [ ] 任務詳細過程會列出成功解析與失敗解析的檔案。

---

### Feature 3: Assignment Input Panel

#### Description
右側區塊提供作業檔案上傳與手動文字輸入，兩者至少提供一項。使用者可以只上傳作業題目檔案、只輸入作業敘述，或同時提供檔案與補充文字。

#### User Roles
- Student User

#### Functional Requirements
- 支援作業檔案上傳。
- 不限制作業檔案格式；可解析的檔案抽取內容，其他格式保留 metadata。
- 提供作業敘述文字框。
- 作業檔案與作業敘述至少提供一項。
- 若選擇作業敘述，文字需至少 10 個字。
- 送出前做前端與後端驗證。

#### UI Requirements
- 右側上方：作業檔案上傳框。
- 右側中段：作業敘述文字輸入框。
- 右側下方：AI 決定輸出檔案提示與生成按鈕。
- 顯示字數或 token 估計。

#### Data Requirements
- assignment_text
- assignment_file_ids
- task_id
- created_at

#### Business Rules
- 作業檔案與作業敘述可以同時提供。
- 作業檔案與作業敘述不可同時空白。
- 作業敘述模式下，作業敘述需至少 10 個字。
- 若作業敘述包含「繞過偵測」等不當意圖，系統應顯示警告並改為一般輸出。

#### Error / Empty States
- 兩者皆空：顯示「請上傳作業檔案或輸入作業敘述（至少一項）」。
- 檔案解析失敗：允許只用文字輸入繼續。

#### Acceptance Criteria
- [ ] 未提供作業檔案與作業敘述時不可送出。
- [ ] 同時提供作業檔案與作業敘述時可以送出。
- [ ] 有作業敘述但無檔案可以送出。
- [ ] 上傳作業檔案後能被解析並納入任務。

---

### Feature 4: Agent-driven Deliverable Generation

#### Description
任務完成後的所有交付檔案，皆由 AI Agent 在執行期間透過 `write_text_file`、`write_docx_file`、`write_pdf_file`、`write_xlsx_file` 等 tools 自行寫到任務工作目錄。系統不再使用「AI 回傳 deliverables JSON → 後端轉檔」的模式。

#### User Roles
- Student User

#### Functional Requirements
- Agent 自行決定要產生哪些格式、幾份檔案、各檔用途。
- 每次 tool call 寫入後，立即在 GeneratedFile 表新增一筆記錄並開放下載。
- 同一任務可包含多份不同用途、不同格式的檔案。
- Agent 必須在每次 `write_*_file` 呼叫提供：`filename`、`purpose`、結構化內容。
- Tool 在後端落地時做格式驗證與安全檢查。

#### UI Requirements
- 結果頁顯示「Agent 寫出的檔案」清單，每筆顯示用途、格式、檔名、下載連結、寫入時間。
- 進度區可即時顯示「Agent 剛寫入 xxx.docx」等訊息。

#### Data Requirements
- 見 [Entity: GeneratedFile](#entity-generatedfile)（紀錄由哪個 tool call 產生）。

#### Business Rules
- 只允許白名單副檔名：`.txt`、`.md`、`.docx`、`.pdf`、`.xlsx`。
- 檔名由後端 sanitize（移除路徑分隔字元、限制長度）。
- 檔案統一寫到 `data/generated/{task_id}/`，禁止跨任務存取。
- 單一檔案大小上限由 Admin 設定（預設 10MB）。
- 同任務最多寫出檔案數有上限（預設 8），避免 Agent 失控。

#### Error / Empty States
- 單一 tool call 失敗：在 trace 顯示錯誤，Agent 可選擇重試或改用其他格式繼續。
- Agent 完全沒寫出任何檔案：仍可只顯示純文字講解，提示使用者「Agent 本次未產生下載檔」。

#### Acceptance Criteria
- [ ] 所有下載檔都來自 Agent 的 `write_*_file` tool call。
- [ ] 寫檔過程可被前端即時看到。
- [ ] 單一檔案 tool call 失敗不影響其他檔案。
- [ ] 檔名與路徑安全（不允許 path traversal）。

---

### Feature 5: AI Agent Loop with Tool Use

#### Description
後端整合 OpenAI-compatible API 的 **tool calling** 模式，為每個任務啟動一個 Agent loop：
1. 組合系統提示詞 + 使用者輸入摘要 + tool catalog。
2. 呼叫 LLM 取得下一輪 tool calls。
3. 後端執行 tool（讀檔、寫進度、寫檔案、累積引用 / 限制）。
4. 把 tool 結果回灌給 LLM，再進入下一輪。
5. 直到 LLM 呼叫 `finish` 或達到 `max_iterations` 上限。

#### User Roles
- Student User（觸發任務）
- Admin User（設定模型、上限）

#### Functional Requirements
- 支援可設定 base URL、API Key、model name、temperature、max output tokens。
- 支援 `max_iterations`（預設 20）。
- 每次 tool call 都會寫入 AgentToolCall 紀錄，並轉換成 ProgressEvent 推送給前端。
- Tool catalog 包含三類：輸入讀取、進度與註記、檔案寫出，以及 `finish`。
- LLM 必須只能透過 tool 操作系統，不能直接傳回任意 JSON 結果。
- Agent 最終的純文字講解透過 `finish(explanation, ...)` 提供。

#### UI Requirements
- 前端顯示「Agent 思考中」、目前迭代次數。
- 即時列出最近的 tool call 名稱與簡短訊息。
- 顯示模型名稱，但不顯示 API Key。

#### Data Requirements
- 任務參數：`api_provider`、`base_url`、`model_name`、`prompt_version`、`max_iterations`、`temperature`。
- Agent 輸出：`title`、`assignment_summary`、`explanation`（由 `finish` 提供）。
- 紀錄：AgentToolCall（每次 tool call 的輸入 / 輸出摘要、狀態、耗時）。

#### Business Rules
- API Key 必須由後端環境變數或後台安全設定管理。
- 不可把 API Key 或 chain-of-thought（thinking）傳到前端。
- 若 LLM 不支援 tool calling，後台需顯示警示，該任務直接失敗。
- 達到 `max_iterations` 仍未 `finish`，Agent 強制結束並標記為 `failed`，已寫出的檔案仍保留。
- 若使用者要求規避偵測，Agent 系統提示詞要求 Agent 拒絕該部分並改為一般輸出。

#### Error / Empty States
- API timeout、rate limit、invalid API key、model unavailable、context too long：寫入錯誤 ProgressEvent 並標記任務失敗。
- 單一 tool call 失敗：把錯誤訊息回灌給 LLM，由 Agent 自行決定要重試或改用其他 tool。

#### Acceptance Criteria
- [ ] 系統能透過 tool calling 完成 Agent loop。
- [ ] 每次 tool call 都有紀錄並可被前端看到。
- [ ] 達到 `max_iterations` 仍未完成的任務會被標記為 `failed` 且不會無限佔資源。
- [ ] 任務完成時，講解、引用、限制、檔案清單都存在。

---

### Feature 6: Real-time Progress and Detailed Process View

#### Description
系統在 AI 任務執行期間即時顯示目前進度，並讓使用者點擊查看詳細流程。

#### User Roles
- Student User
- Demo Evaluator

#### Functional Requirements
- 使用 Server-Sent Events 或 WebSocket 顯示進度。
- 每個階段新增一筆 progress event。
- 詳細過程顯示可公開的處理資訊。
- 禁止顯示敏感資訊、完整 API prompt、API Key 或模型隱藏推理。

#### UI Requirements
- 進度條或步驟列表。
- 即時狀態文字。
- 「查看詳細過程」按鈕。
- 詳細過程 modal、drawer 或 collapsible panel。

#### Data Requirements
- event_id
- task_id
- event_type
- message
- detail
- created_at

#### Business Rules
- 詳細過程應顯示「可驗證的處理紀錄」，不是模型內部 chain-of-thought。
- 詳細過程可包含：需求拆解、引用來源、摘要、大綱、警告、錯誤。

#### Error / Empty States
- 連線中斷：顯示「進度連線中斷，正在嘗試重新連線」。
- 無詳細資料：顯示「目前尚無詳細紀錄」。

#### Acceptance Criteria
- [ ] 任務進行時能即時更新狀態。
- [ ] 使用者能查看詳細過程。
- [ ] 詳細過程不暴露敏感資料。

---

### Feature 7: History Records

#### Description
系統保存使用者任務紀錄，讓使用者可回到歷史頁查看過去輸入、輸出、下載檔案與處理狀態。

#### User Roles
- Student User
- Admin User

#### Functional Requirements
- 建立任務時寫入紀錄。
- 任務完成後更新結果與下載連結。
- 使用者可查看自己的歷史任務。
- Admin 可查看所有任務摘要。
- 支援刪除自己的任務紀錄。

#### UI Requirements
- 歷史紀錄頁。
- 任務列表。
- 任務狀態標籤。
- 查看結果按鈕。
- 下載檔案按鈕。

#### Data Requirements
- task_id
- user_id
- assignment_text
- input_file_summary
- output_text
- generated_files
- status
- created_at
- updated_at

#### Business Rules
- Student User 只能看自己的任務。
- Admin 可看任務摘要，但敏感內容應限制顯示。
- 可設定任務保留天數。

#### Error / Empty States
- 無歷史紀錄：顯示「目前尚無任務紀錄」。
- 任務檔案已刪除：顯示「檔案已過期或不存在」。

#### Acceptance Criteria
- [ ] 完成任務後會出現在歷史紀錄。
- [ ] 使用者不可查看其他人的紀錄。
- [ ] Admin 可查看任務狀態與統計摘要。

---

### Feature 8: Admin Settings Panel

#### Description
後台提供系統設定功能，讓開發者或管理者修改 API 與系統參數。

#### User Roles
- Admin User

#### Functional Requirements
- 設定 API base URL。
- 設定模型名稱。
- 設定 temperature。
- 設定 max output tokens。
- 設定系統提示詞（含 Agent 行為指引）。
- 設定 Agent `max_iterations`（預設 20，可調整）。
- 設定單檔大小、單任務最多檔案數。
- 啟用或停用個別 tool（例如禁用 `write_pdf_file`）。
- 測試 API 連線（含 tool calling 可用性）。

#### UI Requirements
- 後台設定頁。
- 表單欄位。
- 儲存按鈕。
- 測試連線按鈕。
- 成功 / 失敗提示。

#### Data Requirements
- setting_id
- key
- value
- encrypted_value
- updated_by
- updated_at

#### Business Rules
- API Key 必須加密或只存於環境變數。
- API Key 顯示時只顯示遮罩。
- 系統提示詞修改需保留版本紀錄。

#### Error / Empty States
- 連線測試失敗。
- 欄位格式錯誤。
- 權限不足。

#### Acceptance Criteria
- [ ] Admin 能修改非敏感設定。
- [ ] API Key 不會明文外洩。
- [ ] 設定後能影響新任務。

---

### Feature 9: Agent Tool Workspace

#### Description
為每個任務建立沙箱化工作目錄與一組受控 tools，作為 Agent 唯一可使用的副作用通道。Agent 只能透過這些 tools 讀輸入、寫進度、寫檔案、累積引用與限制，並用 `finish` 結束任務。

#### User Roles
- Student User（間接使用，由 Agent 代為操作）
- Admin User（設定 tool 上限與啟停）

#### Functional Requirements
- 每個任務分配 `data/generated/{task_id}/` 工作目錄；Agent 無法寫入其他位置。
- 所有 tool call 都記錄：name、arguments 摘要、result 摘要、status、duration、created_at。
- 提供下列 tools（完整 schema 見 `agents.md` §13 Agent Tool Catalog）：
  - 讀輸入：`list_inputs`、`read_input_text`、`read_input_table`
  - 註記：`log_progress`、`add_reference`、`add_limitation`
  - 寫檔：`write_text_file`、`write_docx_file`、`write_pdf_file`、`write_xlsx_file`
  - 完成：`finish`
- 每個 tool 都有單次呼叫上限（payload 大小、文字長度、列數）。

#### UI Requirements
- 詳細過程頁顯示 tool call timeline。
- 結果頁顯示 Agent 寫出檔案清單。

#### Data Requirements
- 見 [Entity: AgentToolCall](#entity-agenttoolcall) 與 [Entity: GeneratedFile](#entity-generatedfile)。

#### Business Rules
- 副檔名白名單：`.txt`、`.md`、`.docx`、`.pdf`、`.xlsx`。
- 檔名由後端 sanitize，禁止路徑分隔符與相對路徑。
- 同檔名再次寫入 → 覆寫，並寫一筆新的 AgentToolCall。
- `finish` 之後的所有 tool call 一律忽略並標記 `ignored`。
- Tool 結果回灌給 LLM 時超出長度上限要做截斷，避免 context 爆掉。

#### Error / Empty States
- Tool 參數錯誤：回傳結構化錯誤訊息給 LLM，由 Agent 自行修正後重試。
- 工作目錄寫入失敗：寫錯誤 ProgressEvent，任務標記失敗。

#### Acceptance Criteria
- [ ] Agent 無法寫到工作目錄以外的路徑。
- [ ] 所有 tool call 都有紀錄與時序。
- [ ] Tool 上限可由 Admin 設定。
- [ ] 被禁用的 tool 不會出現在發給 LLM 的 tool catalog 中。

---

## 6. Pages / Screens

| Page / Screen | Purpose | Main Components | Access Role |
|---|---|---|---|
| Student Login Page | 學生驗證 | 密碼框、登入按鈕、錯誤訊息 | Guest |
| Admin Login Page | 管理者驗證 | 密碼框、登入按鈕、錯誤訊息 | Guest |
| Main App Page | 建立 AI 任務 | 左側課程資料上傳、右側作業檔案上傳、文字輸入、AI 決定輸出提示、生成按鈕 | Student User |
| Progress Panel | 顯示任務進度 | 進度條、階段列表、詳細過程按鈕 | Student User |
| Detail Process View | 顯示可公開處理紀錄 | 檔案解析摘要、需求拆解、大綱、引用來源、警告 | Student User |
| Result Page / Result Panel | 顯示輸出結果 | AI 講解、複製按鈕、交付檔案用途、下載連結 | Student User |
| History Page | 查看歷史任務 | 任務列表、狀態、查看結果、下載 | Student User / Admin |
| Admin Settings Page | 管理系統設定 | API 設定、模型設定、提示詞、檔案限制 | Admin User |
| Error Page | 顯示例外情境 | 錯誤說明、返回按鈕、重試按鈕 | All |

---

## 7. Data Model

### 7.1 Entities

#### Entity: User

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | Unique identifier |
| email | string | No | OAuth / 正式版使用 |
| display_name | string | No | 使用者名稱 |
| role | enum | Yes | guest / student / admin |
| auth_provider | string | No | password / google / school_sso |
| created_at | datetime | Yes | Created timestamp |
| updated_at | datetime | Yes | Updated timestamp |

#### Entity: Session

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | Session identifier |
| user_id | uuid | No | Linked user |
| role | enum | Yes | Session role |
| expires_at | datetime | Yes | Expiry time |
| created_at | datetime | Yes | Created timestamp |

#### Entity: Task

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | Task identifier |
| user_id | uuid | No | Task owner |
| assignment_text | text | Yes | User-provided assignment description |
| status | enum | Yes | pending / processing / completed / failed |
| input_summary | text | No | Summary of parsed input |
| agent_title | string | No | Title provided by Agent via `finish` |
| agent_assignment_summary | text | No | Assignment summary provided by Agent via `finish` |
| agent_explanation | text | No | Final explanation text provided by Agent via `finish` |
| iterations_used | integer | No | Number of LLM rounds used in the Agent loop |
| model_name | string | No | Model used for this task |
| error_message | text | No | Failure reason |
| created_at | datetime | Yes | Created timestamp |
| updated_at | datetime | Yes | Updated timestamp |

#### Entity: UploadedFile

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | File identifier |
| task_id | uuid | Yes | Related task |
| user_id | uuid | No | Owner |
| file_category | enum | Yes | course_material / assignment_file |
| original_filename | string | Yes | Original filename |
| stored_path | string | Yes | Local or storage path |
| file_type | string | Yes | pdf / docx / txt / md / xlsx / csv |
| file_size | integer | Yes | Size in bytes |
| parse_status | enum | Yes | pending / success / failed |
| parsed_text | text | No | Extracted text |
| parsed_table_json | json | No | Extracted table data |
| error_message | text | No | Parse error |
| created_at | datetime | Yes | Created timestamp |

#### Entity: ProgressEvent

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | Event identifier |
| task_id | uuid | Yes | Related task |
| event_type | string | Yes | upload / parse / analyze / generate / export / error |
| message | string | Yes | Short progress message |
| detail | json | No | Public detail information |
| created_at | datetime | Yes | Created timestamp |

#### Entity: GeneratedFile

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | Generated file identifier |
| task_id | uuid | Yes | Related task |
| tool_call_id | uuid | Yes | The AgentToolCall that produced this file |
| format | enum | Yes | pdf / docx / xlsx / txt / md |
| filename | string | Yes | Filename declared by Agent (sanitized) |
| purpose | text | No | Purpose declared by Agent |
| file_path | string | Yes | File storage path on disk |
| download_url | string | No | Download URL |
| size_bytes | integer | No | File size |
| status | enum | Yes | success / failed |
| error_message | text | No | Export error |
| created_at | datetime | Yes | Created timestamp |

#### Entity: AgentToolCall

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | Tool call identifier |
| task_id | uuid | Yes | Related task |
| iteration | integer | Yes | LLM round number (1-based) |
| tool_name | string | Yes | Tool name, e.g. `write_docx_file` |
| arguments_json | json | Yes | Truncated arguments sent by LLM |
| result_json | json | No | Truncated result returned to LLM |
| status | enum | Yes | success / error / ignored |
| error_message | text | No | Tool error |
| duration_ms | integer | No | Execution time |
| created_at | datetime | Yes | Created timestamp |

#### Entity: Reference

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | Reference identifier |
| task_id | uuid | Yes | Related task |
| source_name | string | Yes | Source file name or label |
| quote_or_summary | text | No | Quote or summary used |
| used_for | text | No | What the Agent used it for |
| created_at | datetime | Yes | Created timestamp |

#### Entity: Limitation

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | Limitation identifier |
| task_id | uuid | Yes | Related task |
| text | text | Yes | Limitation message |
| created_at | datetime | Yes | Created timestamp |

#### Entity: SystemSetting

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | Setting identifier |
| key | string | Yes | Setting key |
| value | text | No | Non-sensitive value |
| encrypted_value | text | No | Sensitive encrypted value |
| updated_by | uuid | No | Admin user id |
| updated_at | datetime | Yes | Updated timestamp |

#### Entity: SystemSettingHistory

| Field | Type | Required | Description |
|---|---|---|---|
| id | uuid | Yes | History record identifier |
| setting_id | uuid | Yes | Related SystemSetting |
| key | string | Yes | Setting key |
| old_value | text | No | Previous value |
| new_value | text | No | New value |
| updated_by | uuid | No | Admin user id |
| updated_at | datetime | Yes | Change timestamp |

### 7.2 Relationships

- User has many Task.
- Task belongs to User.
- Task has many UploadedFile.
- Task has many ProgressEvent.
- Task has many AgentToolCall.
- Task has many GeneratedFile（every GeneratedFile points back to one AgentToolCall）.
- Task has many Reference.
- Task has many Limitation.
- Admin User can update SystemSetting.
- SystemSetting has many SystemSettingHistory.

---

## 8. API / Integration Requirements

### 8.1 Internal APIs

| Endpoint | Method | Purpose | Auth Required | Notes |
|---|---|---|---|---|
| /api/auth/student/login | POST | 學生密碼登入 | No | 共用密碼，建立帶唯一識別的 session |
| /api/auth/admin/login | POST | Admin 密碼登入 | No | 管理者密碼 |
| /api/auth/logout | POST | 登出 | Yes | 清除 session |
| /api/tasks | POST | 建立 AI 任務 | Yes | 接收文字、格式、檔案 metadata |
| /api/tasks/{task_id} | GET | 取得任務詳情 | Yes | 只能讀取自己的任務 |
| /api/tasks/{task_id}/events | GET | SSE 進度串流 | Yes | 回傳 progress events，含 Agent tool call 摘要 |
| /api/tasks/{task_id}/agent-trace | GET | 取得完整 tool call 紀錄 | Yes | 供詳細過程頁顯示 timeline |
| /api/tasks/{task_id}/files | POST | 上傳檔案 | Yes | course_material 或 assignment_file |
| /api/tasks/{task_id}/generated | GET | 取得 Agent 寫出檔案清單 | Yes | 結果頁使用 |
| /api/tasks/{task_id}/download/{file_id} | GET | 下載 Agent 寫出檔案 | Yes | 檢查權限 |
| /api/history | GET | 任務歷史列表 | Yes | Student 看自己的；Admin 可看全部摘要 |
| /api/admin/settings | GET | 取得系統設定 | Admin | 敏感值遮罩 |
| /api/admin/settings | PUT | 更新系統設定 | Admin | 需要驗證欄位 |
| /api/admin/test-api | POST | 測試 AI API 連線 | Admin | 不保存測試內容 |

### 8.2 Third-party Integrations

| Service | Purpose | Required Data | Notes |
|---|---|---|---|
| OpenRouter（OpenAI-compatible） | AI 內容生成 | base URL、API Key、model name、prompt、input content | API Key 僅後端使用，預設 base URL 為 OpenRouter |
| Google OAuth / School SSO | 正式版登入 | client id、client secret、redirect URI | Future / optional for MVP |
| Local File Storage | 儲存上傳檔案與輸出文件 | file path、task id、user id | MVP 可使用本機資料夾 |
| SQLite / PostgreSQL | 儲存任務與設定 | task、file、event、setting records | Demo 可 SQLite；正式版建議 PostgreSQL |

---

## 9. AI-related Requirements

### 9.1 AI Use Case
系統為每個任務啟動一個 **Assignment Drafting Agent**。Agent 透過 OpenAI-compatible API 的 tool calling 介面，多輪呼叫一組受控 tools 來：讀取使用者輸入、累積引用與限制、寫出交付檔案，最後呼叫 `finish` 提供講解。系統不會自動送交外部平台。

### 9.2 Agent Inputs
- 使用者輸入的作業敘述、上傳的作業檔案解析文字，至少一項。
- 上傳的課程資料解析文字與表格摘要。
- 任務基本資訊（task_id、display_name、output 偏好提示）。
- 系統提示詞（含學術誠信、繁體中文、tool use 規範）。
- Tool catalog（由後端注入，包含目前啟用的 tools schema）。

### 9.3 Agent Outputs

Agent 的輸出由兩個來源組成，**完全由 tool calls 產出**，不再使用一次性 JSON：

1. **副作用（tool calls 期間累積）**：
   - 透過 `log_progress` 寫入的 ProgressEvent
   - 透過 `add_reference` 累積的 Reference 列表
   - 透過 `add_limitation` 累積的 Limitation 列表
   - 透過 `write_text_file` / `write_docx_file` / `write_pdf_file` / `write_xlsx_file` 寫出的 GeneratedFile
2. **最終總結（透過 `finish` 提供）**：
   ```json
   {
     "title": "string",
     "assignment_summary": "string",
     "explanation": "string"
   }
   ```
   `finish` 呼叫後，Agent loop 立即結束，此後的 tool call 一律 ignore。

### 9.4 Prompting Rules
- Agent 必須使用 `zh-TW` 台灣正體中文回覆與寫檔，不提供語言切換。
- 文法、用語、詞彙、標點與語氣需符合台灣常用書面中文，不使用簡體字或中國大陸用語。
- Agent 必須明確判斷本次作業輸入模式是「作業敘述文字」或「作業檔案」。
- Agent 必須在 `explanation` 與寫入內容中區分「根據上傳資料可得知」與「Agent 推論或建議」。
- Agent 應先用 `read_input_*` 讀取資料，再決定要產出哪些檔案。
- Agent 可以寫出接近繳交格式的檔案，例如 PDF 繳交版。
- Agent 不得聲稱已送交外部平台、學校系統或老師信箱。
- Agent 不得協助規避偵測、偽造引用或捏造不存在的資料來源。
- Agent 若缺少足夠資料，應透過 `add_limitation` 列出缺少資訊，而不是捏造。
- Agent 引用課程資料，需透過 `add_reference` 記錄來源檔名與摘要。
- Agent 必須在所有產出檔案的尾端加上學術誠信提醒與人工確認清單（由 tool 自動附加或由 Agent 顯式寫入皆可，視 §13 tool 設計）。

### 9.5 Tool-Use Boundary
- Agent 對檔案、進度、引用、限制的任何副作用，**只能**透過 tools 完成。
- 後端不再有「依 deliverables JSON 轉檔」的步驟；檔案在 tool 執行時就直接落地。
- 後端不得在 Agent loop 結束後再「補產」任何 Agent 未呼叫的格式。
- 二進位檔（DOCX、PDF、XLSX）的內容組裝由 tool 實作層負責，Agent 只提供結構化參數（heading、paragraph、bullet、table、rows）。
- Tool 結果回灌 LLM 時要做摘要 / 截斷，避免 context 爆掉。

### 9.6 Agent Tool Catalog（摘要）

完整 schema 見 [`agents.md` §13](agents.md#13-agent-tool-catalog)。

| Tool | 類別 | 用途 |
|---|---|---|
| `list_inputs` | read | 列出本任務所有上傳檔案的 metadata 與解析狀態 |
| `read_input_text(file_id, max_chars)` | read | 讀取已解析的文字內容（自動截斷） |
| `read_input_table(file_id)` | read | 讀取已解析的表格 JSON |
| `log_progress(stage, message)` | annotate | 寫一筆 ProgressEvent，前端 SSE 看到 |
| `add_reference(source_name, quote_or_summary, used_for)` | annotate | 新增引用來源 |
| `add_limitation(text)` | annotate | 新增限制說明 |
| `write_text_file(filename, content, purpose)` | write | 寫出 TXT / MD |
| `write_docx_file(filename, blocks, purpose)` | write | 寫出 DOCX（blocks 為結構化段落） |
| `write_pdf_file(filename, blocks, purpose)` | write | 寫出 PDF（同上 blocks 結構） |
| `write_xlsx_file(filename, sheets, purpose)` | write | 寫出 XLSX（多 sheet） |
| `finish(title, assignment_summary, explanation)` | end | 結束 Agent loop |

### 9.7 Agent Execution Loop

完整流程見 [`agents.md` §14](agents.md#14-agent-execution-loop)。摘要：

1. 後端組裝 system prompt + user prompt（含輸入摘要）+ tool catalog。
2. 呼叫 LLM `chat.completions` 並開啟 tool calling。
3. 若回應包含 `tool_calls`：
   - 依序執行每個 tool，寫入 AgentToolCall 與對應副作用（ProgressEvent / GeneratedFile / Reference / Limitation）。
   - 把 tool 結果作為 `role=tool` 訊息加回對話。
   - 進入下一輪。
4. 若回應呼叫 `finish`：寫入 Task 的 `agent_title` / `agent_assignment_summary` / `agent_explanation`，將狀態設為 `completed`。
5. 若達 `max_iterations` 仍未 `finish`：標記 `failed`，但保留已寫出的檔案。

---

## 10. Non-functional Requirements

### 10.1 Performance
- 一般文字任務應在可接受時間內完成，Demo 建議控制在 30 至 90 秒內。
- 單檔預設限制 10MB。
- 任務執行期間前端不得卡死，需顯示進度。
- 長文件需先摘要再送入 AI。

### 10.2 Security
- API Key 不得出現在前端、console 或 client bundle。
- 密碼與敏感設定不可硬編碼。
- 檔案下載需檢查 session 與權限。
- 上傳檔案需檢查副檔名與 MIME type。
- 後端需驗證所有輸入。
- Admin API 需檢查 Admin 權限。

### 10.3 Privacy
- 使用者檔案與輸出結果只供該使用者存取。
- 任務紀錄應可刪除。
- 系統應避免把敏感內容寫入不必要的 log。
- Demo 資料應使用非敏感範例檔案。

### 10.4 Accessibility
- 所有按鈕需有清楚文字。
- 錯誤訊息需可讀。
- 表單欄位需有 label。
- 主要流程可用鍵盤操作。

### 10.5 Reliability
- API 失敗時需回報錯誤並保留任務狀態。
- 文件輸出失敗時仍保留文字結果。
- SSE 中斷時可重新取得任務狀態。
- 檔案解析失敗不一定中止整個任務。

---

## 11. Technical Recommendations

### 11.1 Suggested Tech Stack

| Layer | Recommendation | Reason |
|---|---|---|
| Frontend | React + Vite + Tailwind CSS | 適合左右分欄、進度 UI、結果頁與後台頁面 |
| Backend | FastAPI | Python 生態、API 清楚、適合非同步任務與 SSE |
| Agent Loop | OpenAI Python SDK + tool calling | OpenRouter / OpenAI-compatible 端點皆原生支援 tool calling，後端只要管 loop |
| Database | SQLite for Demo；PostgreSQL for Production | 期末 Demo 可快速開發，正式版可擴充 |
| Auth | MVP: password session；Future: Google OAuth / School SSO | 符合期末 Demo 與未來擴充 |
| File Parsing | PyMuPDF / python-docx / pandas / openpyxl / vision-capable AI model | 不限制上傳格式；常見文件、表格、圖片會解析，其他格式保留 metadata |
| Document Export | python-docx / reportlab or WeasyPrint / openpyxl | 產生 DOCX、PDF、XLSX |
| Hosting | Docker + Nginx Proxy Manager | 透過 Docker 容器化部署，搭配 Nginx Proxy Manager 反向代理至公開網址 |
| Background Task | FastAPI BackgroundTasks or Celery | 任務時間較長時避免 blocking |
| Progress Update | Server-Sent Events | 比 WebSocket 簡單，適合單向進度更新 |

### 11.2 Architecture Notes
- 前端負責登入頁、任務建立 UI、上傳檔案、進度顯示、結果顯示與後台設定頁。
- 後端負責 session 驗證、檔案解析、任務建立、**Agent loop 執行**、tool 實作、歷史紀錄與權限檢查。
- AI API Key 僅存在後端環境變數或安全設定中，不得暴露給前端。
- 任務建立後，後端寫入 Task，啟動 Agent loop。Loop 內每個 tool call 都會寫入 AgentToolCall 並衍生 ProgressEvent / GeneratedFile / Reference / Limitation。
- 前端透過 SSE 監聽 ProgressEvent，並可呼叫 `/agent-trace` 取得完整 tool call timeline。
- 任務完成（`finish`）後，前端顯示 Agent 講解與檔案下載清單。

### 11.3 Suggested Service Layout
- `agent_runtime.py`：實作 Agent loop（組訊息、呼叫 LLM、dispatch tool、回灌結果、達上限終止）。
- `tools/` package：每個 tool 一個 module（讀輸入 / 註記 / 寫檔 / finish），共用 sanitize、size limit 工具。
- `file_parser_service.py`：仍負責使用者上傳檔案的解析。
- `progress_service.py`：寫 ProgressEvent 與 SSE 廣播。
- `system_setting_service.py`：管理 model、prompt、max_iterations、tool enable 狀態。

---

## 12. Analytics & Tracking

| Event | Trigger | Properties | Purpose |
|---|---|---|---|
| login_success | 使用者登入成功 | role, timestamp | 了解登入使用情況 |
| login_failed | 密碼錯誤 | timestamp | 偵測登入問題 |
| task_created | 使用者建立任務 | file_count, generated_formats | 追蹤核心使用量 |
| file_uploaded | 檔案上傳成功 | file_type, file_size, category | 了解檔案使用情況 |
| file_parse_failed | 檔案解析失敗 | file_type, error_type | 改善解析穩定度 |
| ai_generation_started | AI 任務開始 | model_name, input_length | 追蹤 AI 使用 |
| ai_generation_failed | AI 任務失敗 | error_type, model_name | 偵測 API 問題 |
| output_downloaded | 使用者下載文件 | format, task_id | 了解輸出格式偏好 |
| history_viewed | 使用者查看歷史紀錄 | role | 了解功能使用情況 |
| admin_setting_updated | Admin 修改設定 | setting_key | 追蹤系統設定變更 |

---

## 13. Admin / Operations Requirements

- 管理 API base URL、model name、temperature、max tokens。
- 管理系統提示詞。
- 管理上傳檔案大小限制。
- 管理可用輸出格式。
- 查看任務狀態與錯誤摘要。
- 測試 API 連線。
- 匯出 Demo 測試紀錄。
- 刪除過期任務與檔案。
- 遮罩顯示 API Key，不可完整明文顯示。

---

## 14. QA & Testing Plan

### 14.1 Test Scenarios
- 未登入使用者嘗試進入主系統。
- 使用者輸入錯誤密碼。
- 使用者登入後上傳 PDF、DOCX、TXT、MD、XLSX、CSV、PNG、JPG、WEBP。
- 使用者未提供作業檔案與作業敘述直接送出。
- 使用者同時提供作業檔案與作業敘述。
- 使用者只輸入文字、不上傳檔案。
- 使用者只上傳作業檔案、不輸入文字。
- AI 決定產生 PDF / DOCX / XLSX / 純文字輸出。
- AI API 正常回傳。
- AI API timeout。
- 文件輸出失敗但文字結果成功。
- 使用者查看歷史紀錄。
- Admin 修改 API 設定。
- Student 嘗試進入 Admin 頁面。

### 14.2 Edge Cases
- 檔案過大。
- 檔案副檔名偽裝。
- PDF 沒有可解析文字。
- Excel 多工作表。
- 輸入文字過長。
- SSE 中斷。
- 任務執行中重新整理頁面。
- 下載連結對應檔案不存在。
- 非 Admin 呼叫 Admin API。
- 使用者要求規避偵測。

### 14.3 Regression Checklist
- [ ] 登入 / 登出正常。
- [ ] 未登入不可進入主頁。
- [ ] 任意格式檔案可正常上傳。
- [ ] 未知格式會保留 metadata，不因格式被拒絕。
- [ ] 作業輸入必須包含作業檔案或作業敘述至少一項。
- [ ] AI 生成正常。
- [ ] 進度顯示正常。
- [ ] 詳細過程正常。
- [ ] PDF 輸出正常。
- [ ] DOCX 輸出正常。
- [ ] XLSX 輸出正常。
- [ ] 純文字複製正常。
- [ ] 歷史紀錄正常。
- [ ] Admin 設定正常。
- [ ] API Key 不外洩。

---

## 15. Milestones

| Milestone | Deliverable | Estimated Scope | Dependencies |
|---|---|---|---|
| M1 | 基礎專案架構 | FastAPI、React、路由、基本 UI | 無 |
| M2 | 登入與權限 | 密碼登入、session、保護路由 | M1 |
| M3 | 檔案上傳與解析 | 不限制上傳格式；常見文件、表格、圖片會解析，其他格式保留 metadata | M1 |
| M4 | AI API 串接 | OpenAI-compatible API、prompt、錯誤處理 | M3 |
| M5 | 進度與詳細過程 | SSE、ProgressEvent、詳細紀錄 UI | M4 |
| M6 | 輸出文件 | TXT、DOCX、PDF、XLSX 產生與下載 | M4 |
| M7 | 歷史紀錄 | 任務列表、結果查看、下載 | M6 |
| M8 | Admin 後台 | API 設定、模型設定、檔案限制 | M7 |
| M9 | QA 與 Demo 包裝 | 測試資料、展示流程、修 bug | M8 |

---

## 16. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| 系統被理解成會自動提交作業 | High | Medium | 明確標示不會送交外部平台，只產生可下載檔案 |
| API Key 外洩 | High | Medium | Key 僅後端存取，不傳前端，log 遮罩 |
| 上傳檔案解析失敗 | Medium | High | 顯示警告，允許略過失敗檔案，用文字輸入繼續 |
| AI 輸出錯誤 | High | High | 加入限制聲明、引用來源與清楚的檔案用途 |
| Demo 時 API timeout | Medium | Medium | 準備範例輸入、確保錯誤提示清楚，可手動重試 |
| 文件輸出格式錯亂 | Medium | Medium | 先用固定模板產生，PDF/DOCX/XLSX 分別測試 |
| 範圍過大導致做不完 | High | Medium | MVP 優先完成登入、上傳、AI、進度、輸出；OAuth 與進階 RAG 延後 |
| 歷史紀錄涉及隱私 | Medium | Medium | 使用者只能看自己的任務，提供刪除功能 |
| SSE 連線不穩 | Low | Medium | 提供 task status polling fallback |
| Excel 輸出不適合文字作業 | Low | Medium | 用 Summary / Answer / References / Checklist 多 sheet 格式處理 |
| Agent 在 loop 內無限呼叫 tool / 消耗 token | High | Medium | 強制 `max_iterations`、每個 tool 有大小上限、Admin 可禁用個別 tool |
| Agent 走偏：呼叫了一堆 read 卻不寫檔 | Medium | Medium | 系統提示詞明確要求順序；達上限時保留已寫檔並標記失敗 |
| Tool 結果太大撐爆 LLM context | High | Medium | Tool 實作層對回傳值做摘要與截斷後再回灌 |
| LLM 不支援 tool calling | High | Low | 後台測試連線時驗證並警示，該模型直接拒用 |

---

## 17. Open Questions

### Resolved
- Google Login / SSO：Future Scope，MVP 不做。
- Demo 部署：透過 Docker + Nginx Proxy Manager 部署到公開網址。
- API Provider：確定使用 OpenRouter（OpenAI-compatible）。
- Mock mode：不需要。
- 前端框架：React + Vite + Tailwind CSS。
- 登入機制：學生與 Admin 分開登入頁。學生用共用密碼 + session/cookie 區分身份；Admin 用管理者密碼。
- 系統提示詞版本紀錄：需要，透過 SystemSettingHistory 記錄變更歷史。

- 歷史紀錄：保留完整上傳檔案，不只保留摘要。
- Demo 範例資料：不需要內建範例，Demo 時手動上傳即可。
- AI 輸出語言：固定繁體中文，不做語言切換。
- 學生身份辨識：登入時輸入暱稱，同暱稱可關聯歷史紀錄。

### Still Open
（目前無）

---

## 18. Final Acceptance Criteria

整體專案完成時，必須符合以下條件：

- [ ] 使用者可以通過登入頁進入主系統。
- [ ] 未登入使用者無法直接存取主系統、歷史紀錄與後台。
- [ ] 主頁包含左側課程資料上傳區與右側作業輸入區。
- [ ] 支援任意格式檔案上傳；常見文件、表格、圖片會解析，其他格式保留 metadata。
- [ ] 作業輸入必須包含作業檔案或作業敘述至少一項。
- [ ] Agent 可以決定產生 PDF、DOCX、XLSX、純文字輸出，並透過 tools 寫出。
- [ ] 系統可以成功串接 OpenAI-compatible API 的 tool calling 模式。
- [ ] Agent loop 有迭代上限保護，達上限會安全終止。
- [ ] 任務執行時能顯示即時進度（含 tool call 訊息）。
- [ ] 使用者可以查看詳細處理過程（tool call timeline、引用、限制）。
- [ ] 系統完成後能顯示 Agent 講解與 Agent 寫出檔案的下載連結。
- [ ] 結果包含 Agent 講解、引用來源、限制說明與檔案下載連結。
- [ ] 任務會保存到歷史紀錄。
- [ ] Admin 可以管理 API 與系統設定。
- [ ] API Key 不會出現在前端或下載文件中。
- [ ] 系統有基本錯誤處理與防呆提示。
- [ ] Demo 流程可穩定展示完整輸入、處理、輸出流程。
