import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, History, LogOut, AlertTriangle } from 'lucide-react';
import { getMe, logout } from '../api/auth';
import { createTask, uploadFile, getTask, createEventSource } from '../api/tasks';
import FileUploader from '../components/FileUploader';
import OutputFormatSelector from '../components/OutputFormatSelector';
import ProgressPanel from '../components/ProgressPanel';
import DetailedProcessPanel from '../components/DetailedProcessPanel';
import ResultViewer from '../components/ResultViewer';
import DownloadLinks from '../components/DownloadLinks';
import ErrorAlert from '../components/ErrorAlert';
import LoadingIndicator from '../components/LoadingIndicator';
import type { TaskData } from '../types/task';

export default function MainAppPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<{ user_id: string; display_name: string; role: string } | null>(null);

  const [courseMaterials, setCourseMaterials] = useState<File[]>([]);
  const [assignmentFiles, setAssignmentFiles] = useState<File[]>([]);
  const [assignmentText, setAssignmentText] = useState('');
  const [outputFormats, setOutputFormats] = useState<string[]>(['txt', 'docx', 'pdf']);
  const [integrityChecked, setIntegrityChecked] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');

  const [currentTask, setCurrentTask] = useState<TaskData | null>(null);
  const [progressEvents, setProgressEvents] = useState<{ event_type: string; message: string }[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    getMe().then(setUser).catch(() => navigate('/login'));
    return () => { eventSourceRef.current?.close(); };
  }, [navigate]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const hasText = assignmentText.trim().length > 0;
  const hasFiles = assignmentFiles.length > 0;
  const canSubmit = (hasText || hasFiles) && integrityChecked && outputFormats.length > 0;

  const handleSubmit = async () => {
    setError('');
    setWarning('');

    if (!hasText && !hasFiles) {
      setError('請輸入作業敘述或上傳作業檔案（至少擇一）');
      return;
    }
    if (hasText && assignmentText.trim().length < 10) {
      setError('作業敘述需至少 10 個字');
      return;
    }
    if (!integrityChecked) {
      setError('請先勾選學術誠信確認');
      return;
    }
    if (outputFormats.length === 0) {
      setError('請至少選擇一種輸出格式');
      return;
    }

    setSubmitting(true);
    setCurrentTask(null);
    setProgressEvents([]);

    try {
      const result = await createTask(assignmentText, outputFormats, hasFiles);
      const taskId = result.task_id;
      if (result.warning) setWarning(result.warning);

      const allFiles = [
        ...courseMaterials.map((f) => ({ file: f, category: 'course_material' })),
        ...assignmentFiles.map((f) => ({ file: f, category: 'assignment_file' })),
      ];
      for (const { file, category } of allFiles) {
        await uploadFile(taskId, file, category);
      }

      // Start SSE
      eventSourceRef.current?.close();
      const es = createEventSource(taskId);
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setProgressEvents((prev) => [...prev, data]);

          if (data.event_type === 'complete' || data.event_type === 'done') {
            es.close();
            getTask(taskId).then(setCurrentTask);
          }
          if (data.event_type === 'error' && data.message.startsWith('任務失敗')) {
            es.close();
            getTask(taskId).then(setCurrentTask);
          }
        } catch {}
      };

      es.onerror = () => {
        es.close();
        setTimeout(() => {
          getTask(taskId).then(setCurrentTask);
        }, 2000);
      };
    } catch (err: any) {
      setError(err.response?.data?.detail || '任務建立失敗');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setCurrentTask(null);
    setProgressEvents([]);
    setCourseMaterials([]);
    setAssignmentFiles([]);
    setAssignmentText('');
    setIntegrityChecked(false);
    setWarning('');
    setError('');
  };

  if (!user) return <LoadingIndicator />;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-800">AI 課業輔助系統</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{user.display_name}</span>
            <button
              onClick={() => navigate('/history')}
              className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50"
            >
              <History className="w-4 h-4" /> 歷史紀錄
            </button>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
            >
              <LogOut className="w-4 h-4" /> 登出
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-4">
            <ErrorAlert message={error} onClose={() => setError('')} />
          </div>
        )}
        {warning && (
          <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />
            <p className="text-sm text-amber-700">{warning}</p>
          </div>
        )}

        {/* Show result if task completed */}
        {currentTask && currentTask.status === 'completed' && currentTask.structured_output_json ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">生成結果</h2>
              <button
                onClick={resetForm}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                建立新任務
              </button>
            </div>
            <DownloadLinks taskId={currentTask.id} files={currentTask.generated_files} />
            <ResultViewer data={currentTask.structured_output_json} />
            <DetailedProcessPanel events={currentTask.progress_events} />
          </div>
        ) : currentTask && currentTask.status === 'failed' ? (
          <div className="space-y-4">
            <ErrorAlert message={`任務失敗：${currentTask.error_message || '未知錯誤'}`} />
            <button
              onClick={resetForm}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              重新建立任務
            </button>
            <DetailedProcessPanel events={currentTask.progress_events} />
          </div>
        ) : progressEvents.length > 0 ? (
          <div className="max-w-2xl mx-auto space-y-4">
            <h2 className="text-lg font-semibold text-gray-800">任務處理中</h2>
            <ProgressPanel events={progressEvents} status="processing" />
          </div>
        ) : (
          /* Main form - left/right split */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Course materials */}
            <div className="space-y-4">
              <div className="bg-white rounded-lg border p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-1">課程資料</h2>
                <p className="text-sm text-gray-500 mb-4">上傳講義、筆記、舊作業等參考資料（可選）</p>
                <FileUploader
                  files={courseMaterials}
                  onFilesChange={setCourseMaterials}
                  label="課程資料上傳"
                />
                {courseMaterials.length === 0 && (
                  <p className="text-xs text-gray-400 mt-3">未提供課程資料，AI 將只根據作業需求生成</p>
                )}
              </div>
            </div>

            {/* Right: Assignment input */}
            <div className="space-y-4">
              <div className="bg-white rounded-lg border p-6 space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-800 mb-1">作業輸入</h2>
                  <p className="text-sm text-gray-500">上傳作業檔案並輸入作業敘述</p>
                </div>

                <FileUploader
                  files={assignmentFiles}
                  onFilesChange={setAssignmentFiles}
                  label="作業檔案上傳（可選）"
                />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    作業敘述 <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={assignmentText}
                    onChange={(e) => setAssignmentText(e.target.value)}
                    placeholder="請輸入作業需求、題目說明或你希望 AI 協助的內容..."
                    rows={6}
                    className="w-full border rounded-lg px-4 py-3 text-sm resize-y focus:ring-2 focus:ring-blue-300 focus:border-blue-400 outline-none"
                  />
                  <p className="text-xs text-gray-400 mt-1">{assignmentText.length} 字</p>
                </div>

                <OutputFormatSelector selected={outputFormats} onChange={setOutputFormats} />

                {/* Academic integrity checkbox */}
                <label className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-4 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={integrityChecked}
                    onChange={(e) => setIntegrityChecked(e.target.checked)}
                    className="mt-1"
                  />
                  <span className="text-sm text-amber-700">
                    我理解此輸出為 AI 輔助生成的草稿，需自行檢查、修改並遵守課程規範，不應直接提交作為作業。
                  </span>
                </label>

                <button
                  onClick={handleSubmit}
                  disabled={submitting || !canSubmit}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg py-3 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  <Send className="w-4 h-4" />
                  {submitting ? '建立任務中...' : '開始生成'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
