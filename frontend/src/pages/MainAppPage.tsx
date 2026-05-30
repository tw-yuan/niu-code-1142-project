import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import FilePickerCard from '../components/FilePickerCard'
import { useSession } from '../auth/SessionContext'
import { createTask, runTask, uploadFiles } from '../api/tasks'

export default function MainAppPage() {
  const { session } = useSession()
  const navigate = useNavigate()

  const [courseFiles, setCourseFiles] = useState<File[]>([])
  const [assignmentFiles, setAssignmentFiles] = useState<File[]>([])
  const [assignmentText, setAssignmentText] = useState('')
  const [acknowledge, setAcknowledge] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasFile = assignmentFiles.length > 0
  const hasText = assignmentText.trim().length >= 10
  const canSubmit = (hasFile || hasText) && acknowledge && !submitting

  async function onSubmit() {
    setError(null)
    if (!hasFile && !hasText) {
      setError('請上傳作業檔案或輸入作業敘述（至少 10 字）')
      return
    }
    if (!acknowledge) {
      setError('請先勾選學術誠信確認')
      return
    }
    setSubmitting(true)
    try {
      const task = await createTask(assignmentText.trim())
      if (courseFiles.length > 0) {
        await uploadFiles(task.id, courseFiles, 'course_material')
      }
      if (assignmentFiles.length > 0) {
        await uploadFiles(task.id, assignmentFiles, 'assignment_file')
      }
      await runTask(task.id)
      navigate(`/tasks/${task.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '建立任務失敗')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="max-w-6xl mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">建立新任務</h1>
          <p className="text-sm text-slate-600 mt-1">
            歡迎，{session?.display_name ?? '學生'}。左側可選擇上傳課程資料，右側必填作業檔案或作業敘述。
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <FilePickerCard
            title="課程資料（選填）"
            subtitle="講義、參考資料、之前作業等，幫助 AI 理解上下文。"
            files={courseFiles}
            onChange={setCourseFiles}
          />

          <div className="space-y-6">
            <FilePickerCard
              title="作業檔案"
              subtitle="作業題目、需求說明、需要分析的資料表等。"
              files={assignmentFiles}
              onChange={setAssignmentFiles}
            />

            <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <header>
                <h2 className="font-semibold text-slate-900">作業敘述</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  與作業檔案至少擇一；若兩者皆填，AI 會同時參考。
                </p>
              </header>
              <textarea
                value={assignmentText}
                onChange={(e) => setAssignmentText(e.target.value)}
                placeholder="請描述作業要求、輸出格式、字數限制、評分重點等。"
                rows={6}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                maxLength={20000}
              />
              <div className="text-xs text-slate-400 text-right">{assignmentText.length} / 20000</div>
            </section>
          </div>
        </div>

        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <label className="flex gap-3 items-start cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledge}
              onChange={(e) => setAcknowledge(e.target.checked)}
              className="mt-1 h-4 w-4"
            />
            <div className="text-sm text-amber-900">
              <strong>學術誠信確認：</strong>我了解 AI 產出僅為草稿，需自行審閱與修改；本系統不會自動送交作業，
              也不協助規避抄襲或 AI 偵測。
            </div>
          </label>
        </section>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onSubmit}
            disabled={!canSubmit}
            className="rounded-xl bg-blue-600 text-white px-6 py-3 font-medium hover:bg-blue-700 disabled:bg-slate-300 disabled:text-slate-500"
          >
            {submitting ? '建立任務中…' : '開始生成'}
          </button>
        </div>
      </main>
    </div>
  )
}
