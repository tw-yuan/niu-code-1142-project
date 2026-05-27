import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Trash2, Eye, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { getHistory, getTask, deleteTask } from '../api/tasks';
import { getMe } from '../api/auth';
import ResultViewer from '../components/ResultViewer';
import DownloadLinks from '../components/DownloadLinks';
import DetailedProcessPanel from '../components/DetailedProcessPanel';
import LoadingIndicator from '../components/LoadingIndicator';
import type { HistoryItem, TaskData } from '../types/task';

const STATUS_MAP: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  pending: { icon: <Clock className="w-4 h-4" />, label: '等待中', color: 'text-gray-500 bg-gray-100' },
  processing: { icon: <Loader2 className="w-4 h-4 animate-spin" />, label: '處理中', color: 'text-blue-600 bg-blue-100' },
  completed: { icon: <CheckCircle className="w-4 h-4" />, label: '完成', color: 'text-green-600 bg-green-100' },
  failed: { icon: <AlertCircle className="w-4 h-4" />, label: '失敗', color: 'text-red-600 bg-red-100' },
};

export default function HistoryPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<TaskData | null>(null);
  const [loadingTask, setLoadingTask] = useState(false);

  useEffect(() => {
    getMe().catch(() => navigate('/login'));
    loadHistory();
  }, [navigate]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await getHistory();
      setItems(data);
    } catch {}
    setLoading(false);
  };

  const viewTask = async (id: string) => {
    setLoadingTask(true);
    try {
      const data = await getTask(id);
      setSelectedTask(data);
    } catch {}
    setLoadingTask(false);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('確定要刪除此任務紀錄？')) return;
    try {
      await deleteTask(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      if (selectedTask?.id === id) setSelectedTask(null);
    } catch {}
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <button onClick={() => navigate('/app')} className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800">
            <ArrowLeft className="w-4 h-4" /> 返回主頁
          </button>
          <h1 className="text-lg font-bold text-gray-800">歷史紀錄</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {selectedTask ? (
          <div className="space-y-4">
            <button
              onClick={() => setSelectedTask(null)}
              className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
            >
              <ArrowLeft className="w-4 h-4" /> 返回列表
            </button>
            {selectedTask.structured_output_json && (
              <>
                <DownloadLinks taskId={selectedTask.id} files={selectedTask.generated_files} />
                <ResultViewer data={selectedTask.structured_output_json} />
              </>
            )}
            <DetailedProcessPanel events={selectedTask.progress_events} />
          </div>
        ) : loading ? (
          <LoadingIndicator message="載入歷史紀錄..." />
        ) : items.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <Clock className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>目前尚無任務紀錄</p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => {
              const st = STATUS_MAP[item.status] || STATUS_MAP.pending;
              return (
                <div
                  key={item.id}
                  className="bg-white border rounded-lg p-4 flex items-center gap-4"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 truncate">{item.assignment_text}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${st.color}`}>
                        {st.icon} {st.label}
                      </span>
                      <span className="text-xs text-gray-400">
                        {new Date(item.created_at).toLocaleString('zh-TW')}
                      </span>
                      {item.input_summary && (
                        <span className="text-xs text-gray-400">{item.input_summary}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {item.has_output && (
                      <button
                        onClick={() => viewTask(item.id)}
                        disabled={loadingTask}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50"
                      >
                        <Eye className="w-4 h-4" /> 查看
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
