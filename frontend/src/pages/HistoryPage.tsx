import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { listSessions, deleteSession, updateSession } from "../api/sessions";
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
  const [query, setQuery] = useState("");
  const [direction, setDirection] = useState("all");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
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

  async function saveTitle(id: number) {
    const updated = await updateSession(id, { title: draftTitle.trim() || null });
    setSessions((prev) => prev.map((s) => (s.id === id ? updated : s)));
    setRenamingId(null);
    setDraftTitle("");
  }

  const directions = Array.from(new Set(sessions.map((s) => s.direction_label)));
  const filtered = sessions.filter((s) => {
    const q = query.trim().toLowerCase();
    const matchesQuery = !q || [
      s.title,
      s.direction_label,
      s.document_original_filename,
      s.last_message_preview,
    ].some((item) => item?.toLowerCase().includes(q));
    const matchesDirection = direction === "all" || s.direction_label === direction;
    return matchesQuery && matchesDirection;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main className="max-w-3xl mx-auto px-6 py-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-6">學習歷史</h2>
        <div className="mb-5 grid gap-3 sm:grid-cols-[1fr_180px]">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜尋講義、方向、摘要"
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-300"
          >
            <option value="all">全部方向</option>
            {directions.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="text-center text-gray-400 py-16">載入中...</div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-5xl mb-4">📭</div>
            <p className="text-gray-500">還沒有任何學習記錄</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-sm text-gray-400">沒有符合條件的學習記錄</div>
        ) : (
          <div className="grid gap-3">
            {filtered.map((s) => (
              <div
                key={s.id}
                onClick={() => navigate(`/sessions/${s.id}`)}
                className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:border-indigo-300 hover:shadow-sm transition-all group"
              >
                <div className="text-2xl flex-shrink-0">{s.direction_emoji || "💬"}</div>
                <div className="flex-1 min-w-0">
                  {renamingId === s.id ? (
                    <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        value={draftTitle}
                        onChange={(e) => setDraftTitle(e.target.value)}
                        className="min-w-0 flex-1 rounded-md border border-gray-200 px-2 py-1 text-sm"
                        autoFocus
                      />
                      <button onClick={() => saveTitle(s.id)} className="text-xs text-indigo-600">儲存</button>
                      <button onClick={() => setRenamingId(null)} className="text-xs text-gray-400">取消</button>
                    </div>
                  ) : (
                    <div className="font-medium text-gray-800 group-hover:text-indigo-700">
                      {s.title || s.direction_label}
                    </div>
                  )}
                  <div className="text-xs text-gray-400 truncate mt-0.5">
                    {s.document_original_filename} · {formatDate(s.created_at)}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-400">
                    <span>{s.direction_label}</span>
                    <span>{s.message_count} 則訊息</span>
                    {s.quiz_attempts > 0 && <span>測驗 {s.quiz_attempts} 次</span>}
                    {typeof s.quiz_average_score === "number" && <span>平均 {s.quiz_average_score} 分</span>}
                  </div>
                  {s.last_message_preview && (
                    <div className="mt-2 truncate text-xs text-gray-400">{s.last_message_preview}</div>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setRenamingId(s.id);
                    setDraftTitle(s.title || s.direction_label);
                  }}
                  className="text-gray-300 hover:text-indigo-500 transition-colors px-2 flex-shrink-0"
                >
                  ✎
                </button>
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
