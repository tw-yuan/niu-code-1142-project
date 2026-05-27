# project.md

## 1. Project Overview

### 1.1 Project Name
AI 課業輔助與作業草稿生成系統

### 1.2 One-line Description
一個以 Python FastAPI 為後端、串接 OpenAI-compatible API 的期末專題 Web 系統，讓使用者上傳課程資料與作業需求，由 AI 產生可檢視處理過程、可引用來源、可下載成多種格式的課業輔助草稿。

### 1.3 Background / Problem
學生在處理期末報告、程式作業、數據分析作業、閱讀心得或混合型作業時，通常需要同時整理講義、理解作業要求、規劃回答架構、產生初稿、轉換輸出格式。本專案希望展示一個 AI 輔助型網頁系統，讓使用者能集中上傳課程資料與作業需求，並由 AI 產生結構化草稿、解題輔助、引用來源與可下載文件。

本專案應定位為「課業輔助、草稿生成、學習整理與人工審核工具」，而不是「全自動代寫作業系統」。系統輸出需包含學術誠信聲明、人工確認步驟、引用來源與自我檢查清單。

### 1.4 Business / Product Goals
- 完成一個可在期末專題中展示的 AI Web App Demo。
- 展示 Python 後端、前端介面、檔案解析、AI API 串接、即時進度、文件輸出等整合能力。
- 支援使用者上傳課程資料與作業需求，產生結構化作業草稿或解題輔助內容。
- 支援 PDF、Word、Excel、純文字等多格式輸出。
- 提供可檢視的處理流程、來源引用與人工確認機制。

### 1.5 Success Metrics
- 使用者能在通過驗證後成功進入主系統。
- 使用者能成功上傳支援格式的課程資料與作業檔案。
- 使用者能手動輸入作業敘述並送出任務。
- 系統能顯示即時處理進度與詳細處理紀錄。
- 系統能成功呼叫 OpenAI-compatible API 並回傳結果。
- 系統能產生至少三種輸出格式：純文字、DOCX、PDF。
- 系統能在 Demo 情境中穩定完成至少 3 種作業類型測試。
- 系統輸出包含學術誠信提醒、引用來源與人工確認清單。

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
  - 選擇輸出格式。
  - 查看處理進度。
  - 查看詳細過程。
  - 下載或複製結果。

#### Persona 2: Demo Evaluator / Teacher
- Description: 評分老師或專題展示觀眾，用來檢查系統功能完整性、技術整合能力與倫理設計。
- Goals:
  - 看到系統從輸入到輸出的完整流程。
  - 確認 AI 串接與文件輸出可正常運作。
  - 確認系統有安全限制與學術誠信設計。
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
| Student User | 上傳檔案、輸入作業敘述、選擇輸出格式、建立 AI 任務、查看自己的任務結果 | 修改系統 API 設定、查看其他使用者任務 | MVP 可用共用密碼；正式版使用 OAuth / 帳號登入 |
| Admin User | 管理 API endpoint、模型名稱、系統提示詞、檔案限制、任務紀錄 | 直接查看不屬於管理目的的敏感內容 | 後台操作需更高權限 |
| Demo Evaluator | 使用測試資料體驗完整流程 | 修改 API Key 或刪除資料 | 可使用測試帳號或測試密碼 |

---

## 3. Scope Definition

### 3.1 MVP Scope
第一版必須完成的功能：

- 密碼驗證或簡化登入頁。
- 主系統頁面採左右分欄：
  - 左側：課程相關資料上傳區，可選。
  - 右側：作業檔案上傳區與作業敘述文字輸入區。
- 支援上傳格式：PDF、DOCX、TXT、MD、XLSX、CSV。
- 支援輸出格式：PDF、DOCX、XLSX、純文字顯示。
- 串接 OpenAI-compatible API，預設支援可自訂 base URL、API Key、model name。
- 顯示即時處理進度。
- 顯示詳細處理過程頁籤或展開區塊。
- 顯示引用來源與資料使用摘要。
- 完成後顯示 AI 結果、複製按鈕與下載連結。
- 儲存歷史紀錄，包括任務輸入摘要、輸出結果、檔案下載路徑與建立時間。
- 管理後台，可設定 API endpoint、模型名稱、系統提示詞、檔案大小限制與啟用輸出格式。
- 基本錯誤處理與防呆提示。
- 學術誠信聲明與人工確認清單。

### 3.2 Out of Scope
第一版明確不做的事項：

- 自動登入學校 LMS 或替使用者提交作業。
- 繞過抄襲偵測、規避 AI 偵測或隱藏 AI 使用痕跡。
- 保證答案正確或保證符合任課老師評分標準。
- 複雜多租戶 SaaS 權限系統。
- 付款功能。
- 手機 App。
- 即時多人協作編輯。
- 對大型影片、音訊或圖片作業進行完整解析。
- 使用者之間共享作業結果。

### 3.3 Future Scope
後續版本可考慮的功能：

- Google Login 或學校 SSO 登入。
- 使用者分級與管理員邀請機制。
- 任務歷史搜尋、篩選與標籤。
- RAG 向量檢索，支援大量課程資料。
- 上傳圖片或掃描檔 OCR。
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
3. 右側上傳作業檔案，可選。
4. 使用者在文字框輸入作業敘述，必填。
5. 使用者選擇輸出格式。
6. 使用者勾選「我理解此輸出需自行檢查與修改，不應直接提交」。
7. 使用者按下「開始生成」。
8. 系統建立任務紀錄（Task）。
9. 系統將使用者已選擇的檔案上傳至後端，關聯至該 Task。
10. 系統進入檔案解析、需求分析、內容生成、格式輸出流程。

#### Edge Cases
- 使用者未輸入作業敘述。
- 使用者未上傳任何檔案，但有輸入文字。
- 檔案格式不支援。
- 檔案大小超過限制。
- 上傳檔案解析失敗。
- API Key 錯誤。
- API timeout。

#### Acceptance Criteria
- [ ] 使用者至少需要輸入作業敘述才可送出。
- [ ] 系統支援無課程資料但有文字作業敘述的情境。
- [ ] 系統會拒絕不支援格式並顯示原因。
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
   - 課程資料整理中
   - 作業需求分析中
   - 產生回答架構中
   - 生成草稿中
   - 檢查引用與格式中
   - 建立輸出檔案中
   - 任務完成
4. 使用者可點擊「查看詳細過程」。
5. 系統顯示可公開的處理紀錄：
   - 已解析檔案清單
   - 每份檔案擷取到的文字摘要
   - 作業需求拆解
   - 回答大綱
   - 使用資料來源列表
   - 輸出格式建立紀錄
   - 系統警告或限制

#### Edge Cases
- SSE 連線中斷。
- 使用者重新整理頁面。
- 後端任務仍在執行但前端斷線。
- 任務失敗。

#### Acceptance Criteria
- [ ] 使用者可看到即時進度文字。
- [ ] 使用者可展開詳細過程。
- [ ] 詳細過程不得顯示 API Key、系統敏感設定或模型不可公開的內部推理內容。
- [ ] 若任務失敗，系統顯示失敗階段與可重試建議。

---

### Journey 4: 取得輸出結果

#### User Story
As a Student User, I want to download or copy the AI-generated result, so that I can review, edit, and use it as a learning draft.

#### Flow
1. 任務完成後，系統顯示 AI 生成結果。
2. 若使用者選擇純文字，系統顯示可複製文字區塊。
3. 若使用者選擇 PDF、DOCX 或 XLSX，系統顯示下載按鈕。
4. 系統在結果上方顯示學術誠信提醒。
5. 系統在結果下方顯示人工確認清單。

#### Edge Cases
- 文件產生失敗但文字結果成功。
- 下載連結過期或檔案不存在。
- Excel 輸出不適合非表格型內容。

#### Acceptance Criteria
- [ ] 使用者能複製純文字結果。
- [ ] 使用者能下載所選格式文件。
- [ ] 文件內容需包含標題、作業需求摘要、生成內容、引用來源、人工確認清單。
- [ ] 如果某格式產生失敗，系統應保留文字結果並提示重新產生文件。

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
- 支援格式：PDF、DOCX、TXT、MD、XLSX、CSV。
- 顯示每個檔案名稱、大小、狀態。
- 可移除已選檔案。
- 檔案為可選，不是必填。
- 上傳後後端解析文字與表格內容。

#### UI Requirements
- 左側標題：「課程資料，可選」。
- 拖放上傳區。
- 檔案清單。
- 格式與大小限制說明。

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
- 不支援格式不得送出。
- 單檔大小限制預設 10MB，可由 Admin 調整。
- 檔案解析失敗不一定中止整個任務，但需顯示警告。

#### Error / Empty States
- 未上傳：顯示「未提供課程資料，AI 將只根據作業需求生成」。
- 解析失敗：顯示「此檔案無法解析，已略過」。

#### Acceptance Criteria
- [ ] 使用者能上傳支援格式檔案。
- [ ] 系統能顯示上傳檔案清單。
- [ ] 系統能拒絕不支援格式。
- [ ] 任務詳細過程會列出成功解析與失敗解析的檔案。

---

### Feature 3: Assignment Input Panel

#### Description
右側區塊提供作業檔案上傳與手動文字輸入，兩者可並用。文字輸入為必填，避免 AI 不知道任務目標。

#### User Roles
- Student User

#### Functional Requirements
- 支援作業檔案上傳。
- 支援格式：PDF、DOCX、TXT、MD、XLSX、CSV。
- 提供作業敘述文字框。
- 作業敘述為必填。
- 送出前做前端與後端驗證。

#### UI Requirements
- 右側上方：作業檔案上傳框。
- 右側中段：作業敘述文字輸入框。
- 右側下方：輸出格式選擇與生成按鈕。
- 顯示字數或 token 估計。

#### Data Requirements
- assignment_text
- assignment_file_ids
- task_id
- created_at

#### Business Rules
- 作業敘述不可空白。
- 作業敘述需至少 10 個字。
- 若作業敘述包含「幫我直接提交」、「繞過偵測」等不當意圖，系統應顯示警告並改為提供學習輔助版本。

#### Error / Empty States
- 文字空白：顯示「請輸入作業需求或題目說明」。
- 檔案解析失敗：允許只用文字輸入繼續。

#### Acceptance Criteria
- [ ] 沒有作業敘述不可送出。
- [ ] 有作業敘述但無檔案可以送出。
- [ ] 上傳作業檔案後能被解析並納入任務。

---

### Feature 4: Output Format Selection

#### Description
使用者可選擇輸出格式，系統完成後產生對應結果。

#### User Roles
- Student User

#### Functional Requirements
- 支援純文字顯示。
- 支援 DOCX 下載。
- 支援 PDF 下載。
- 支援 XLSX 下載。
- 可一次選擇多種格式，或在完成後產生其他格式。
- Excel 輸出需適合表格型內容，若非表格內容則以多 sheet 方式輸出：Summary、Answer、References、Checklist。

#### UI Requirements
- checkbox 或 multi-select。
- 預設選取：純文字、DOCX、PDF。
- XLSX 顯示提示：「適合表格或資料分析型作業」。

#### Data Requirements
- output_formats
- generated_file_paths
- generation_status_by_format

#### Business Rules
- 純文字結果為基礎輸出，其他格式從純文字或結構化 JSON 轉換。
- 如果 PDF / DOCX / XLSX 失敗，不影響純文字結果顯示。

#### Error / Empty States
- 文件產生失敗：顯示「內容已生成，但文件轉換失敗，可下載其他格式或重新產生」。

#### Acceptance Criteria
- [ ] 使用者能選擇輸出格式。
- [ ] 任務完成後能取得對應格式。
- [ ] 文件產生失敗時有清楚錯誤提示。

---

### Feature 5: AI Generation Engine

#### Description
後端整合 OpenAI-compatible API，將課程資料、作業需求、系統提示詞與輸出格式要求組合成請求，生成結構化結果。

#### User Roles
- Student User
- Admin User

#### Functional Requirements
- 支援可設定 base URL。
- 支援可設定 API Key。
- 支援可設定 model name。
- 支援 streaming 或類似任務進度回傳。
- 將輸出要求拆成結構化格式：
  - title
  - assignment_summary
  - generated_answer
  - references
  - limitations
  - academic_integrity_notice
  - human_review_checklist
- 對上傳資料做長度控制與摘要。
- 若內容過長，需先摘要再生成。

#### UI Requirements
- 前端顯示「AI 生成中」。
- 顯示 token / 字數過長警告。
- 顯示模型名稱，但不顯示 API Key。

#### Data Requirements
- api_provider
- base_url
- model_name
- prompt_version
- input_summary
- output_text
- structured_output_json
- token_estimate
- status
- error_message

#### Business Rules
- API Key 必須由後端環境變數或後台安全設定管理。
- 不可把 API Key 傳到前端。
- 模型輸出不得聲稱完全正確。
- 若使用者要求直接提交或規避偵測，系統需改寫為學習輔助輸出。

#### Error / Empty States
- API timeout。
- Rate limit。
- Invalid API key。
- Model unavailable。
- Context too long。

#### Acceptance Criteria
- [ ] 系統能成功呼叫 OpenAI-compatible API。
- [ ] 系統能處理 API 錯誤並顯示可理解訊息。
- [ ] 輸出包含引用來源、限制與人工確認清單。

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
- 設定系統提示詞。
- 設定檔案大小限制。
- 啟用或停用輸出格式。
- 測試 API 連線。

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

## 6. Pages / Screens

| Page / Screen | Purpose | Main Components | Access Role |
|---|---|---|---|
| Student Login Page | 學生驗證 | 密碼框、登入按鈕、錯誤訊息 | Guest |
| Admin Login Page | 管理者驗證 | 密碼框、登入按鈕、錯誤訊息 | Guest |
| Main App Page | 建立 AI 任務 | 左側課程資料上傳、右側作業檔案上傳、文字輸入、格式選擇、生成按鈕 | Student User |
| Progress Panel | 顯示任務進度 | 進度條、階段列表、詳細過程按鈕 | Student User |
| Detail Process View | 顯示可公開處理紀錄 | 檔案解析摘要、需求拆解、大綱、引用來源、警告 | Student User |
| Result Page / Result Panel | 顯示輸出結果 | 結果文字、複製按鈕、下載連結、人工確認清單 | Student User |
| History Page | 查看歷史任務 | 任務列表、狀態、查看結果、下載 | Student User / Admin |
| Admin Settings Page | 管理系統設定 | API 設定、模型設定、提示詞、檔案限制、輸出格式 | Admin User |
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
| output_formats | json | Yes | Selected output formats |
| status | enum | Yes | pending / processing / completed / failed |
| input_summary | text | No | Summary of parsed input |
| output_text | text | No | AI generated result |
| structured_output_json | json | No | Structured result |
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
| format | enum | Yes | pdf / docx / xlsx / txt |
| file_path | string | Yes | File storage path |
| download_url | string | No | Download URL |
| status | enum | Yes | success / failed |
| error_message | text | No | Export error |
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
- Task has many GeneratedFile.
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
| /api/tasks/{task_id}/events | GET | SSE 進度串流 | Yes | 回傳 progress events |
| /api/tasks/{task_id}/files | POST | 上傳檔案 | Yes | course_material 或 assignment_file |
| /api/tasks/{task_id}/download/{file_id} | GET | 下載輸出檔案 | Yes | 檢查權限 |
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
AI 負責將使用者提供的作業敘述、作業檔案與課程資料整理成可讀、可修改、可引用來源的作業輔助草稿。AI 不應被描述為保證正確的自動代寫者，而是草稿與學習輔助生成器。

### 9.2 AI Inputs
- 使用者輸入的作業敘述。
- 上傳的作業檔案解析文字。
- 上傳的課程資料解析文字。
- 表格資料摘要。
- 使用者選擇的輸出格式。
- 系統提示詞。
- 學術誠信與輸出限制規則。

### 9.3 AI Outputs
AI 應輸出結構化內容：

```json
{
  "title": "string",
  "assignment_summary": "string",
  "requirements_breakdown": ["string"],
  "answer_outline": ["string"],
  "generated_draft": "string",
  "references": [
    {
      "source_name": "string",
      "quote_or_summary": "string",
      "used_for": "string"
    }
  ],
  "limitations": ["string"],
  "academic_integrity_notice": "string",
  "human_review_checklist": ["string"]
}
```

### 9.4 Prompting Rules
- AI 必須使用繁體中文回覆，不提供語言切換。
- AI 必須區分「根據上傳資料可得知」與「AI 推論或建議」。
- AI 必須在結果中加入「請自行確認、修改與引用」提醒。
- AI 不得聲稱輸出可直接提交。
- AI 不得協助規避抄襲偵測、AI 偵測、學校規範或評分系統。
- AI 若缺少足夠資料，應列出缺少資訊，而不是捏造。
- AI 若引用課程資料，需標註來源檔名與摘要。
- AI 應優先產生草稿、架構、說明、檢查清單與學習輔助內容。

### 9.5 Guardrails
- 系統需加入學術誠信提示。
- 使用者送出前需勾選確認：「我會自行檢查、修改並遵守課程規範」。
- 若使用者要求「直接幫我完成可提交作業」、「不要被老師發現」、「繞過 AI 偵測」等，系統應拒絕該部分要求，並改為提供學習輔助版本。
- 系統不得產生虛假引用。
- 系統不得隱藏 AI 使用事實。
- 系統不得代替使用者登入學校平台或自動提交作業。

### 9.6 Human Review Requirements
以下 AI 輸出需要使用者人工審核：

- 所有事實性陳述。
- 所有引用來源。
- 所有計算結果。
- 所有程式碼。
- 所有表格數據與結論。
- 所有最終可提交文件。

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
| Database | SQLite for Demo；PostgreSQL for Production | 期末 Demo 可快速開發，正式版可擴充 |
| Auth | MVP: password session；Future: Google OAuth / School SSO | 符合期末 Demo 與未來擴充 |
| File Parsing | PyMuPDF / python-docx / pandas / openpyxl | 支援 PDF、DOCX、TXT、MD、XLSX、CSV |
| Document Export | python-docx / reportlab or WeasyPrint / openpyxl | 產生 DOCX、PDF、XLSX |
| Hosting | Docker + Nginx Proxy Manager | 透過 Docker 容器化部署，搭配 Nginx Proxy Manager 反向代理至公開網址 |
| Background Task | FastAPI BackgroundTasks or Celery | 任務時間較長時避免 blocking |
| Progress Update | Server-Sent Events | 比 WebSocket 簡單，適合單向進度更新 |

### 11.2 Architecture Notes
- 前端負責登入頁、任務建立 UI、上傳檔案、進度顯示、結果顯示與後台設定頁。
- 後端負責 session 驗證、檔案解析、任務建立、AI API 呼叫、文件輸出、歷史紀錄與權限檢查。
- AI API Key 僅存在後端環境變數或安全設定中，不得暴露給前端。
- 任務建立後，後端寫入 Task，並用 ProgressEvent 記錄每個階段。
- 前端透過 SSE 監聽任務進度。
- 任務完成後，後端產生文字結果與所選格式檔案，前端顯示下載連結。

---

## 12. Analytics & Tracking

| Event | Trigger | Properties | Purpose |
|---|---|---|---|
| login_success | 使用者登入成功 | role, timestamp | 了解登入使用情況 |
| login_failed | 密碼錯誤 | timestamp | 偵測登入問題 |
| task_created | 使用者建立任務 | file_count, output_formats | 追蹤核心使用量 |
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
- 使用者登入後上傳 PDF、DOCX、TXT、MD、XLSX、CSV。
- 使用者未輸入作業敘述直接送出。
- 使用者只輸入文字、不上傳檔案。
- 使用者選擇 PDF / DOCX / XLSX / 純文字輸出。
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
- 使用者要求規避偵測或直接提交。

### 14.3 Regression Checklist
- [ ] 登入 / 登出正常。
- [ ] 未登入不可進入主頁。
- [ ] 上傳支援格式正常。
- [ ] 不支援格式會被拒絕。
- [ ] 作業敘述必填。
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
| M3 | 檔案上傳與解析 | 支援 PDF、DOCX、TXT、MD、XLSX、CSV | M1 |
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
| 系統被理解成代寫作業工具 | High | Medium | 明確定位為學習輔助工具，加入學術誠信聲明與人工確認 |
| API Key 外洩 | High | Medium | Key 僅後端存取，不傳前端，log 遮罩 |
| 上傳檔案解析失敗 | Medium | High | 顯示警告，允許略過失敗檔案，用文字輸入繼續 |
| AI 輸出錯誤 | High | High | 加入限制聲明、引用來源、人工確認清單 |
| Demo 時 API timeout | Medium | Medium | 準備範例輸入、確保錯誤提示清楚，可手動重試 |
| 文件輸出格式錯亂 | Medium | Medium | 先用固定模板產生，PDF/DOCX/XLSX 分別測試 |
| 範圍過大導致做不完 | High | Medium | MVP 優先完成登入、上傳、AI、進度、輸出；OAuth 與進階 RAG 延後 |
| 歷史紀錄涉及隱私 | Medium | Medium | 使用者只能看自己的任務，提供刪除功能 |
| SSE 連線不穩 | Low | Medium | 提供 task status polling fallback |
| Excel 輸出不適合文字作業 | Low | Medium | 用 Summary / Answer / References / Checklist 多 sheet 格式處理 |

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
- [ ] 支援 PDF、DOCX、TXT、MD、XLSX、CSV 上傳。
- [ ] 作業敘述為必填。
- [ ] 使用者可以選擇 PDF、DOCX、XLSX、純文字輸出。
- [ ] 系統可以成功串接 OpenAI-compatible API。
- [ ] 任務執行時能顯示即時進度。
- [ ] 使用者可以查看詳細處理過程。
- [ ] 系統完成後能顯示結果與下載連結。
- [ ] 結果包含引用來源、限制說明、學術誠信提醒與人工確認清單。
- [ ] 任務會保存到歷史紀錄。
- [ ] Admin 可以管理 API 與系統設定。
- [ ] API Key 不會出現在前端或下載文件中。
- [ ] 系統有基本錯誤處理與防呆提示。
- [ ] Demo 流程可穩定展示完整輸入、處理、輸出流程。
