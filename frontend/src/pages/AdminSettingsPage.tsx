import { useEffect, useMemo, useState } from 'react'
import AppHeader from '../components/AppHeader'
import {
  getAdminSettings,
  testApi,
  updateAdminSettings,
  type AdminSettingsView,
  type TestApiResult,
} from '../api/admin'
import { ApiError } from '../api/client'

const NEVER_DISABLE = new Set(['finish'])

const TOOL_LABEL: Record<string, string> = {
  list_inputs: '列出輸入',
  read_input_text: '讀取文字',
  read_input_table: '讀取表格',
  log_progress: '進度訊息',
  add_reference: '新增引用',
  add_limitation: '新增限制',
  write_text_file: '寫純文字',
  write_docx_file: '寫 DOCX',
  write_pdf_file: '寫 PDF',
  write_xlsx_file: '寫 XLSX',
  finish: '結束任務',
}

type Draft = {
  system_prompt: string
  model_name: string
  base_url: string
  temperature: string
  max_output_tokens: string
  max_iterations: string
  max_file_size_mb: string
  max_files_per_task: string
  disabled_tools: Set<string>
}

function viewToDraft(v: AdminSettingsView): Draft {
  return {
    system_prompt: v.system_prompt,
    model_name: v.model_name,
    base_url: v.base_url,
    temperature: String(v.temperature),
    max_output_tokens: String(v.max_output_tokens),
    max_iterations: String(v.max_iterations),
    max_file_size_mb: String(v.max_file_size_mb),
    max_files_per_task: String(v.max_files_per_task),
    disabled_tools: new Set(v.disabled_tools),
  }
}

export default function AdminSettingsPage() {
  const [view, setView] = useState<AdminSettingsView | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestApiResult | null>(null)

  useEffect(() => {
    getAdminSettings()
      .then((v) => {
        setView(v)
        setDraft(viewToDraft(v))
      })
      .catch((e) => setError(e instanceof ApiError ? e.detail : '載入設定失敗'))
      .finally(() => setLoading(false))
  }, [])

  const isDirty = useMemo(() => {
    if (!view || !draft) return false
    const a = JSON.stringify({
      ...draft,
      disabled_tools: [...draft.disabled_tools].sort(),
    })
    const b = JSON.stringify({
      ...viewToDraft(view),
      disabled_tools: [...viewToDraft(view).disabled_tools].sort(),
    })
    return a !== b
  }, [view, draft])

  function update<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  function toggleTool(name: string) {
    if (!draft) return
    if (NEVER_DISABLE.has(name)) return
    const next = new Set(draft.disabled_tools)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    update('disabled_tools', next)
  }

  function resetPrompt() {
    if (!view || !draft) return
    update('system_prompt', view.default_system_prompt)
  }

  async function onSave() {
    if (!draft) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const updated = await updateAdminSettings({
        system_prompt: draft.system_prompt,
        model_name: draft.model_name,
        base_url: draft.base_url,
        temperature: Number(draft.temperature),
        max_output_tokens: Number(draft.max_output_tokens),
        max_iterations: Number(draft.max_iterations),
        max_file_size_mb: Number(draft.max_file_size_mb),
        max_files_per_task: Number(draft.max_files_per_task),
        disabled_tools: [...draft.disabled_tools],
      })
      setView(updated)
      setDraft(viewToDraft(updated))
      setSuccess('已儲存')
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  async function onTest() {
    if (!draft) return
    setTesting(true)
    setTestResult(null)
    try {
      const result = await testApi({ base_url: draft.base_url, model_name: draft.model_name })
      setTestResult(result)
    } catch (e) {
      setTestResult({
        ok: false,
        latency_ms: null,
        model: draft.model_name,
        base_url: draft.base_url,
        tool_calling_supported: null,
        detail: e instanceof ApiError ? e.detail : '測試失敗',
      })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="max-w-4xl mx-auto p-6 space-y-6">
        <h1 className="text-2xl font-bold">系統設定</h1>

        {loading && <div className="text-slate-500 text-sm">載入中…</div>}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}
        {success && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>
        )}

        {view && draft && (
          <>
            <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <header className="flex items-center justify-between">
                <h2 className="font-semibold">OpenAI-Compatible API</h2>
                <span className={`text-xs ${view.api_key_configured ? 'text-emerald-600' : 'text-amber-600'}`}>
                  {view.api_key_configured
                    ? `API Key 已設定（${view.api_key_preview ?? '****'}）`
                    : 'API Key 尚未設定（請改環境變數）'}
                </span>
              </header>
              <p className="text-xs text-slate-500">
                API Key 僅由環境變數 <code className="font-mono">OPENAI_COMPATIBLE_API_KEY</code> 提供，不會顯示完整明文，也無法在此編輯。
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <LabeledInput
                  label="Base URL"
                  value={draft.base_url}
                  onChange={(v) => update('base_url', v)}
                />
                <LabeledInput
                  label="Model"
                  value={draft.model_name}
                  onChange={(v) => update('model_name', v)}
                />
                <LabeledInput
                  label="Temperature (0–2)"
                  type="number"
                  step="0.05"
                  value={draft.temperature}
                  onChange={(v) => update('temperature', v)}
                />
                <LabeledInput
                  label="Max output tokens"
                  type="number"
                  value={draft.max_output_tokens}
                  onChange={(v) => update('max_output_tokens', v)}
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={onTest}
                  disabled={testing}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100 disabled:opacity-50"
                >
                  {testing ? '測試中…' : '測試 API 連線'}
                </button>
                {testResult && (
                  <span className={`text-xs ${testResult.ok ? 'text-emerald-600' : 'text-red-600'}`}>
                    {testResult.ok ? `✓ ${testResult.latency_ms} ms` : '✗ '}
                    {testResult.detail}
                  </span>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <header className="flex items-center justify-between">
                <h2 className="font-semibold">Agent Loop 上限</h2>
              </header>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <LabeledInput
                  label="Max iterations"
                  type="number"
                  value={draft.max_iterations}
                  onChange={(v) => update('max_iterations', v)}
                />
                <LabeledInput
                  label="單檔大小 (MB)"
                  type="number"
                  value={draft.max_file_size_mb}
                  onChange={(v) => update('max_file_size_mb', v)}
                />
                <LabeledInput
                  label="單任務最多檔案數"
                  type="number"
                  value={draft.max_files_per_task}
                  onChange={(v) => update('max_files_per_task', v)}
                />
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <header className="flex items-center justify-between">
                <h2 className="font-semibold">Tool 啟用狀態</h2>
              </header>
              <p className="text-xs text-slate-500">
                取消勾選即停用該 tool；finish 為必備工具，不可停用。
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {view.available_tools.map((t) => {
                  const enabled = !draft.disabled_tools.has(t)
                  const locked = NEVER_DISABLE.has(t)
                  return (
                    <label
                      key={t}
                      className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
                        locked ? 'border-slate-200 bg-slate-50 text-slate-500' : 'border-slate-200 bg-white cursor-pointer hover:bg-slate-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={enabled}
                        disabled={locked}
                        onChange={() => toggleTool(t)}
                      />
                      <span className="font-mono text-xs">{t}</span>
                      <span className="text-slate-500 text-xs">{TOOL_LABEL[t] ?? ''}</span>
                    </label>
                  )
                })}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <header className="flex items-center justify-between">
                <h2 className="font-semibold">系統提示詞</h2>
                <button
                  type="button"
                  onClick={resetPrompt}
                  className="text-xs text-blue-600 hover:underline"
                >
                  回到預設值
                </button>
              </header>
              <p className="text-xs text-slate-500">
                每次儲存會在 SystemSettingHistory 留下一筆紀錄。
              </p>
              <textarea
                value={draft.system_prompt}
                onChange={(e) => update('system_prompt', e.target.value)}
                rows={16}
                className="w-full rounded-lg border border-slate-300 p-3 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <div className="text-xs text-slate-400 text-right">
                {draft.system_prompt.length} 字元
              </div>
            </section>

            <div className="sticky bottom-4 z-10 flex justify-end gap-3 bg-slate-50/80 backdrop-blur p-3 rounded-xl">
              <button
                type="button"
                onClick={() => view && setDraft(viewToDraft(view))}
                disabled={!isDirty || saving}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100 disabled:opacity-50"
              >
                取消
              </button>
              <button
                type="button"
                onClick={onSave}
                disabled={!isDirty || saving}
                className="rounded-lg bg-blue-600 text-white px-5 py-2 text-sm font-medium hover:bg-blue-700 disabled:bg-slate-300"
              >
                {saving ? '儲存中…' : '儲存設定'}
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

function LabeledInput({
  label,
  value,
  onChange,
  type = 'text',
  step,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  step?: string
}) {
  return (
    <label className="space-y-1 text-sm">
      <span className="text-slate-700">{label}</span>
      <input
        type={type}
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
    </label>
  )
}
