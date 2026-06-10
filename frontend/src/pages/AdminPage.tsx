import { useEffect, useMemo, useState } from "react";
import AppHeader from "../components/AppHeader";
import ChatBubble from "../components/ChatBubble";
import {
  deleteAdminDocument,
  deleteAdminSession,
  getAdminSession,
  getOverview,
  listAdminDocuments,
  listAdminSessions,
  listAdminUsers,
  retryAdminDocument,
  updateAdminUserRole,
  type AdminDocument,
  type AdminOverview,
  type AdminSession,
  type AdminSessionDetail,
  type AdminUser,
} from "../api/admin";

type Tab = "overview" | "users" | "documents" | "sessions";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [sessions, setSessions] = useState<AdminSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<AdminSessionDetail | null>(null);
  const [loading, setLoading] = useState(true);

  async function reload() {
    setLoading(true);
    try {
      const [overviewData, userData, documentData, sessionData] = await Promise.all([
        getOverview(),
        listAdminUsers(),
        listAdminDocuments(),
        listAdminSessions(),
      ]);
      setOverview(overviewData);
      setUsers(userData);
      setDocuments(documentData);
      setSessions(sessionData);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    queueMicrotask(() => {
      void reload();
    });
  }, []);

  const tabs = useMemo(() => [
    { key: "overview" as const, label: "總覽" },
    { key: "users" as const, label: "使用者" },
    { key: "documents" as const, label: "文件" },
    { key: "sessions" as const, label: "學習紀錄" },
  ], []);

  async function handleRole(user: AdminUser, role: "student" | "admin") {
    const updated = await updateAdminUserRole(user.id, role);
    setUsers((prev) => prev.map((u) => u.id === updated.id ? updated : u));
  }

  async function handleDeleteDocument(doc: AdminDocument) {
    if (!confirm(`確定刪除文件「${doc.original_filename}」？`)) return;
    await deleteAdminDocument(doc.id);
    setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    await getOverview().then(setOverview);
  }

  async function handleRetryDocument(doc: AdminDocument) {
    const updated = await retryAdminDocument(doc.id);
    setDocuments((prev) => prev.map((d) => d.id === updated.id ? updated : d));
  }

  async function handleDeleteSession(session: AdminSession) {
    if (!confirm(`確定刪除「${session.direction_label}」這筆學習紀錄？`)) return;
    await deleteAdminSession(session.id);
    setSessions((prev) => prev.filter((s) => s.id !== session.id));
    if (selectedSession?.id === session.id) setSelectedSession(null);
    await getOverview().then(setOverview);
  }

  async function openSession(session: AdminSession) {
    const detail = await getAdminSession(session.id);
    setSelectedSession(detail);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-800">助教工作台</h1>
            <p className="mt-1 text-sm text-gray-400">追蹤學生學習、講義狀態、測驗互動與系統狀態</p>
          </div>
          <button
            onClick={reload}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-500 hover:border-indigo-300 hover:text-indigo-600"
          >
            重新整理
          </button>
        </div>

        <div className="mb-5 flex gap-2 border-b border-gray-200">
          {tabs.map((item) => (
            <button
              key={item.key}
              onClick={() => setTab(item.key)}
              className={`px-3 py-2 text-sm font-medium border-b-2 ${
                tab === item.key
                  ? "border-indigo-500 text-indigo-600"
                  : "border-transparent text-gray-400 hover:text-gray-700"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="py-16 text-center text-gray-400">載入中...</div>
        ) : (
          <>
            {tab === "overview" && <Overview overview={overview} />}
            {tab === "users" && <Users users={users} onRole={handleRole} />}
            {tab === "documents" && (
              <Documents
                documents={documents}
                onDelete={handleDeleteDocument}
                onRetry={handleRetryDocument}
              />
            )}
            {tab === "sessions" && (
              <Sessions
                sessions={sessions}
                selectedSession={selectedSession}
                onOpen={openSession}
                onDelete={handleDeleteSession}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}

function Overview({ overview }: { overview: AdminOverview | null }) {
  const stats = [
    ["使用者", overview?.users ?? 0],
    ["活躍學生", overview?.active_students ?? 0],
    ["文件", overview?.documents ?? 0],
    ["已解析", overview?.ready_documents ?? 0],
    ["學習紀錄", overview?.sessions ?? 0],
    ["訊息", overview?.messages ?? 0],
    ["失敗文件", overview?.failed_documents ?? 0],
    ["測驗互動", overview?.quiz_attempts ?? 0],
  ];
  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {stats.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-400">{label}</div>
            <div className="mt-2 text-2xl font-semibold text-gray-800">{value}</div>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-3 text-sm font-medium text-gray-700">熱門學習方向</div>
          <div className="grid gap-2">
            {(overview?.top_directions ?? []).map((item) => (
              <div key={item.label} className="flex justify-between text-sm">
                <span className="text-gray-600">{item.label}</span>
                <span className="text-gray-400">{item.count}</span>
              </div>
            ))}
            {(overview?.top_directions ?? []).length === 0 && <div className="text-sm text-gray-400">尚無資料</div>}
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-3 text-sm font-medium text-gray-700">常用講義</div>
          <div className="grid gap-2">
            {(overview?.popular_documents ?? []).map((item) => (
              <div key={item.filename} className="flex justify-between gap-3 text-sm">
                <span className="truncate text-gray-600">{item.filename}</span>
                <span className="shrink-0 text-gray-400">{item.session_count}</span>
              </div>
            ))}
            {(overview?.popular_documents ?? []).length === 0 && <div className="text-sm text-gray-400">尚無資料</div>}
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-3 text-sm font-medium text-gray-700">測驗概況</div>
          <div className="text-sm text-gray-500">
            平均分數：{typeof overview?.quiz_average_score === "number" ? `${overview.quiz_average_score} 分` : "尚無分數"}
          </div>
        </div>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="mb-3 text-sm font-medium text-gray-700">近期學生問題</div>
        <div className="grid gap-3">
          {(overview?.recent_questions ?? []).map((item, index) => (
            <div key={`${item.created_at}-${index}`} className="border-b border-gray-100 pb-3 last:border-0 last:pb-0">
              <div className="text-sm text-gray-700">{item.content}</div>
              <div className="mt-1 text-xs text-gray-400">
                {item.nickname} · {item.document} · {formatDate(item.created_at)}
              </div>
            </div>
          ))}
          {(overview?.recent_questions ?? []).length === 0 && <div className="text-sm text-gray-400">尚無資料</div>}
        </div>
      </div>
    </div>
  );
}

function Users({ users, onRole }: { users: AdminUser[]; onRole: (user: AdminUser, role: "student" | "admin") => void }) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <table className="w-full text-left text-sm">
        <thead className="bg-gray-50 text-xs text-gray-400">
          <tr>
            <th className="px-4 py-3">暱稱</th>
            <th className="px-4 py-3">角色</th>
            <th className="px-4 py-3">文件</th>
            <th className="px-4 py-3">紀錄</th>
            <th className="px-4 py-3">建立時間</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {users.map((user) => (
            <tr key={user.id}>
              <td className="px-4 py-3 font-medium text-gray-700">{user.nickname}</td>
              <td className="px-4 py-3">
                <select
                  value={user.role}
                  onChange={(e) => onRole(user, e.target.value as "student" | "admin")}
                  className="rounded-md border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600"
                >
                  <option value="student">student</option>
                  <option value="admin">admin</option>
                </select>
              </td>
              <td className="px-4 py-3 text-gray-500">{user.document_count}</td>
              <td className="px-4 py-3 text-gray-500">{user.session_count}</td>
              <td className="px-4 py-3 text-gray-400">{formatDate(user.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Documents({
  documents,
  onDelete,
  onRetry,
}: {
  documents: AdminDocument[];
  onDelete: (doc: AdminDocument) => void;
  onRetry: (doc: AdminDocument) => void;
}) {
  return (
    <div className="grid gap-3">
      {documents.map((doc) => (
        <div key={doc.id} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="truncate font-medium text-gray-800">{doc.original_filename}</div>
              <div className="mt-1 text-xs text-gray-400">
                {doc.owner_nickname ?? "未知使用者"} · {doc.file_type} · {formatSize(doc.file_size)} · {doc.token_count.toLocaleString()} tokens · {formatDate(doc.created_at)}
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span className="rounded bg-gray-100 px-2 py-1 text-gray-500">解析：{doc.parse_status}</span>
                <span className="rounded bg-gray-100 px-2 py-1 text-gray-500">索引：{doc.index_status}</span>
              </div>
              {doc.error_message && <div className="mt-2 text-xs text-red-500">{doc.error_message}</div>}
            </div>
            <div className="flex shrink-0 gap-3">
              <button onClick={() => onRetry(doc)} className="text-sm text-gray-300 hover:text-indigo-500">重試</button>
              <button onClick={() => onDelete(doc)} className="text-sm text-gray-300 hover:text-red-500">刪除</button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function Sessions({
  sessions,
  selectedSession,
  onOpen,
  onDelete,
}: {
  sessions: AdminSession[];
  selectedSession: AdminSessionDetail | null;
  onOpen: (session: AdminSession) => void;
  onDelete: (session: AdminSession) => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <div className="grid content-start gap-3">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onOpen(session)}
            className="rounded-lg border border-gray-200 bg-white p-4 text-left hover:border-indigo-300"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="font-medium text-gray-800">{session.direction_emoji} {session.title || session.direction_label}</div>
              <span className="text-xs text-gray-400">{session.message_count} 則</span>
            </div>
            <div className="mt-1 truncate text-xs text-gray-400">
              {session.owner_nickname ?? "未知使用者"} · {session.document_original_filename ?? "未知文件"}
            </div>
            {session.quiz_attempts > 0 && (
              <div className="mt-2 text-xs text-indigo-500">
                測驗 {session.quiz_attempts} 次
                {typeof session.quiz_average_score === "number" ? ` · 平均 ${session.quiz_average_score} 分` : ""}
              </div>
            )}
            <div className="mt-1 text-xs text-gray-300">{formatDate(session.created_at)}</div>
            <div
              onClick={(e) => {
                e.stopPropagation();
                onDelete(session);
              }}
              className="mt-2 inline-block text-xs text-gray-300 hover:text-red-500"
            >
              刪除
            </div>
          </button>
        ))}
      </div>
      <div className="min-h-[420px] rounded-lg border border-gray-200 bg-white p-4">
        {!selectedSession ? (
          <div className="py-24 text-center text-sm text-gray-400">選擇一筆學習紀錄查看對話</div>
        ) : (
          <div>
            <div className="mb-4 border-b border-gray-100 pb-3">
              <div className="font-semibold text-gray-800">{selectedSession.title || selectedSession.direction_label}</div>
              <div className="mt-1 text-xs text-gray-400">
                {selectedSession.owner_nickname ?? "未知使用者"} · {selectedSession.document_original_filename ?? "未知文件"}
              </div>
            </div>
            {selectedSession.messages.map((message) => (
              <ChatBubble key={message.id} message={message} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
