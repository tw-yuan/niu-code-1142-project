import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { listSessions, deleteSession } from "../api/sessions";
import type { LearningSession } from "../api/sessions";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("zh-TW", {
    year: "numeric", month: "long", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<LearningSession[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    listSessions()
      .then(setSessions)
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("確定要刪除這筆學習記錄？")) return;
    await deleteSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main className="max-w-3xl mx-auto px-6 py-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-6">學習歷史</h2>

        {loading ? (
          <div className="text-center text-gray-400 py-16">載入中...</div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-5xl mb-4">📭</div>
            <p className="text-gray-500">還沒有任何學習記錄</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => navigate(`/sessions/${s.id}`)}
                className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:border-indigo-300 hover:shadow-sm transition-all group"
              >
                <div className="text-2xl flex-shrink-0">{s.direction_emoji || "💬"}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-800 group-hover:text-indigo-700">
                    {s.direction_label}
                  </div>
                  <div className="text-xs text-gray-400 truncate mt-0.5">
                    {s.document_original_filename} · {formatDate(s.created_at)}
                  </div>
                </div>
                <button
                  onClick={(e) => handleDelete(s.id, e)}
                  className="text-gray-300 hover:text-red-400 transition-colors px-2 flex-shrink-0"
                >
                  🗑
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
