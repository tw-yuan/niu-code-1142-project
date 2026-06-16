import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import {
  Ban,
  BookOpen,
  CheckCircle2,
  FileText,
  KeyRound,
  LayoutDashboard,
  MessageSquare,
  Plus,
  RefreshCw,
  Save,
  Search,
  Shield,
  SlidersHorizontal,
  Trash2,
  Users,
  UserPlus,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ApiError, apiFetch, CostStats } from "../lib/api";

interface AdminStats {
  users: number;
  documents: number;
  tokens_used: number;
}

interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: "student" | "teacher" | "admin";
  quota_mb: number;
  token_quota: number;
  is_active: number;
  created_at: string;
  deletion_requested_at: string | null;
  deletion_scheduled_at: string | null;
  token_used_this_month: number;
  quota_percent: number;
  quota_status: "ok" | "warning" | "exceeded";
  document_count: number;
  storage_bytes: number;
  documents_by_status: Record<string, number>;
}

interface AdminUserList {
  items: AdminUser[];
  total: number;
  limit: number;
  offset: number;
}

interface AdminUserUsage {
  token_used_this_month: number;
  token_quota: number;
  quota_percent: number;
  by_feature: Record<string, number>;
  by_model: Record<string, number>;
  daily_series: { date: string; tokens: number }[];
  recent_events: Array<{
    id: string;
    feature: string;
    model: string;
    tokens_used: number;
    created_at: string;
  }>;
}

interface AdminUserDetail extends AdminUser {
  usage: AdminUserUsage;
  recent_audit_logs: Array<{
    id: string;
    action: string;
    resource: string | null;
    created_at: string;
  }>;
  deletion: {
    requested_at: string | null;
    scheduled_at: string | null;
    export_expires_at: string | null;
  };
}

interface ReliabilityStats {
  fallback_count_7d: number;
  by_reason: Record<string, number>;
  daily_series: { date: string; count: number }[];
  events: Array<{
    id: string;
    detail: Record<string, unknown>;
    created_at: string;
  }>;
}

interface AdminDocument {
  id: string;
  user_id: string;
  username: string;
  email: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  page_count: number | null;
  chunk_count: number | null;
  error_msg: string | null;
  created_at: string;
  updated_at: string;
}

interface AdminList<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

interface AdminChatSession {
  id: string;
  user_id: string;
  username: string;
  title: string | null;
  doc_ids: string[];
  course_id: string | null;
  mode: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

interface AdminChatDetail extends AdminChatSession {
  messages: Array<{
    id: string;
    role: string;
    content: string;
    token_count: number | null;
    created_at: string;
  }>;
}

interface AdminCourse {
  id: string;
  owner_id: string;
  owner_username: string;
  title: string;
  description: string | null;
  join_code: string;
  is_active: number;
  member_count: number;
  document_count: number;
  created_at: string;
}

interface AdminCourseDetail extends AdminCourse {
  members: Array<{
    user_id: string;
    username: string;
    email: string;
    role: "student" | "ta" | "instructor";
    joined_at: string;
  }>;
  documents: Array<{
    id: string;
    user_id: string;
    username: string;
    filename: string;
    status: string;
    page_count: number | null;
    chunk_count: number | null;
    created_at: string;
  }>;
}

interface UserForm {
  username: string;
  email: string;
  password: string;
  role: "student" | "teacher" | "admin";
  quota_mb: number;
  token_quota: number;
  is_active: number;
}

const emptyForm: UserForm = {
  username: "",
  email: "",
  password: "",
  role: "student",
  quota_mb: 500,
  token_quota: 1_000_000,
  is_active: 1,
};

type AdminTab =
  | "overview"
  | "users"
  | "resources"
  | "courses"
  | "settings"
  | "audit";

export function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [cost, setCost] = useState<CostStats | null>(null);
  const [reliability, setReliability] = useState<ReliabilityStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [selected, setSelected] = useState<AdminUserDetail | null>(null);
  const [auditLogs, setAuditLogs] = useState<Array<Record<string, unknown>>>(
    [],
  );
  const [adminDocuments, setAdminDocuments] = useState<AdminDocument[]>([]);
  const [adminChats, setAdminChats] = useState<AdminChatSession[]>([]);
  const [adminCourses, setAdminCourses] = useState<AdminCourse[]>([]);
  const [selectedChat, setSelectedChat] = useState<AdminChatDetail | null>(
    null,
  );
  const [selectedCourse, setSelectedCourse] =
    useState<AdminCourseDetail | null>(null);
  const [courseMemberUserId, setCourseMemberUserId] = useState("");
  const [courseMemberRole, setCourseMemberRole] = useState<
    "student" | "ta" | "instructor"
  >("student");
  const [courseDocumentId, setCourseDocumentId] = useState("");
  const [configText, setConfigText] = useState("");
  const [configMessage, setConfigMessage] = useState("");
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [adminTab, setAdminTab] = useState<AdminTab>("overview");
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<UserForm>(emptyForm);
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const featureRows = useMemo(
    () =>
      Object.entries(cost?.this_month.by_feature ?? {}).map(
        ([feature, total_usd]) => ({ feature, total_usd }),
      ),
    [cost],
  );
  const selectedFeatureRows = useMemo(
    () =>
      Object.entries(selected?.usage.by_feature ?? {}).map(
        ([feature, tokens]) => ({ feature, tokens }),
      ),
    [selected],
  );

  useEffect(() => {
    loadAll().catch(handleError);
  }, []);

  useEffect(() => {
    loadUsers().catch(handleError);
  }, [q, role, active]);

  async function loadAll() {
    setError("");
    const [nextStats, nextCost, nextReliability, logs, config] =
      await Promise.all([
        apiFetch<AdminStats>("/admin/stats"),
        apiFetch<CostStats>("/admin/stats/cost"),
        apiFetch<ReliabilityStats>("/admin/stats/reliability"),
        apiFetch<Array<Record<string, unknown>>>("/admin/audit-logs?limit=20"),
        apiFetch<Record<string, unknown>>("/admin/config"),
        loadUsers(),
        loadResources(),
      ]);
    setStats(nextStats);
    setCost(nextCost);
    setReliability(nextReliability);
    setAuditLogs(logs);
    setConfigText(JSON.stringify(config, null, 2));
  }

  async function loadUsers() {
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (role) params.set("role", role);
    if (active) params.set("is_active", active);
    params.set("limit", "100");
    const data = await apiFetch<AdminUserList>(
      `/admin/users?${params.toString()}`,
    );
    setUsers(data.items);
    setTotalUsers(data.total);
    if (selected && !data.items.some((user) => user.id === selected.id)) {
      setSelected(null);
    }
  }

  async function loadResources() {
    const [documents, chats, courses] = await Promise.all([
      apiFetch<AdminList<AdminDocument>>("/admin/documents?limit=50"),
      apiFetch<AdminList<AdminChatSession>>("/admin/chat-sessions?limit=50"),
      apiFetch<AdminList<AdminCourse>>("/admin/courses?limit=50"),
    ]);
    setAdminDocuments(documents.items);
    setAdminChats(chats.items);
    setAdminCourses(courses.items);
  }

  async function selectUser(userId: string) {
    setError("");
    setPassword("");
    const detail = await apiFetch<AdminUserDetail>(`/admin/users/${userId}`);
    setSelected(detail);
  }

  async function createUser(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setError("");
    const created = await apiFetch<AdminUser>("/admin/users", {
      method: "POST",
      body: JSON.stringify(createForm),
    });
    setCreateForm(emptyForm);
    setCreateOpen(false);
    setMessage(`已建立 ${created.username}`);
    await loadUsers();
    await selectUser(created.id);
  }

  async function saveSelected() {
    if (!selected) return;
    setMessage("");
    setError("");
    const updated = await apiFetch<AdminUser>(`/admin/users/${selected.id}`, {
      method: "PUT",
      body: JSON.stringify({
        username: selected.username,
        email: selected.email,
        role: selected.role,
        quota_mb: selected.quota_mb,
        token_quota: selected.token_quota,
        is_active: selected.is_active,
      }),
    });
    setMessage(`已更新 ${updated.username}`);
    await loadUsers();
    await selectUser(updated.id);
  }

  async function toggleActive(user: AdminUser) {
    setMessage("");
    setError("");
    await apiFetch<AdminUser>(`/admin/users/${user.id}`, {
      method: "PUT",
      body: JSON.stringify({ is_active: user.is_active ? 0 : 1 }),
    });
    setMessage(user.is_active ? "使用者已停用" : "使用者已啟用");
    await loadUsers();
    if (selected?.id === user.id) await selectUser(user.id);
  }

  async function resetPassword() {
    if (!selected || !password) return;
    setMessage("");
    setError("");
    await apiFetch(`/admin/users/${selected.id}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    setPassword("");
    setMessage("密碼已重設");
  }

  async function forcePurge() {
    if (!selected) return;
    const confirmed = window.confirm(
      `確定要永久清除 ${selected.username} 與所有資料？此操作無法復原。`,
    );
    if (!confirmed) return;
    setMessage("");
    setError("");
    await apiFetch(`/admin/users/${selected.id}/force-purge`, {
      method: "POST",
    });
    setSelected(null);
    setMessage("使用者資料已清除");
    await loadUsers();
  }

  async function deleteAdminDocument(doc: AdminDocument) {
    setMessage("");
    setError("");
    await apiFetch(`/admin/documents/${doc.id}`, { method: "DELETE" });
    setMessage("文件已刪除");
    await loadResources();
  }

  async function openAdminChat(sessionId: string) {
    setSelectedChat(
      await apiFetch<AdminChatDetail>(`/admin/chat-sessions/${sessionId}`),
    );
  }

  async function deleteAdminChat(session: AdminChatSession) {
    setMessage("");
    setError("");
    await apiFetch(`/admin/chat-sessions/${session.id}`, { method: "DELETE" });
    setSelectedChat(null);
    setMessage("對話已刪除");
    await loadResources();
  }

  async function openAdminCourse(courseId: string) {
    setSelectedCourse(
      await apiFetch<AdminCourseDetail>(`/admin/courses/${courseId}`),
    );
  }

  async function saveAdminCourse() {
    if (!selectedCourse) return;
    const updated = await apiFetch<AdminCourseDetail>(
      `/admin/courses/${selectedCourse.id}`,
      {
        method: "PUT",
        body: JSON.stringify({
          title: selectedCourse.title,
          description: selectedCourse.description,
          is_active: selectedCourse.is_active,
        }),
      },
    );
    setSelectedCourse(updated);
    setMessage("課程已更新");
    await loadResources();
  }

  async function deleteAdminCourse(course: AdminCourse) {
    setMessage("");
    setError("");
    await apiFetch(`/admin/courses/${course.id}`, { method: "DELETE" });
    setSelectedCourse(null);
    setMessage("課程已刪除");
    await loadResources();
  }

  async function addCourseMember() {
    if (!selectedCourse || !courseMemberUserId.trim()) return;
    const updated = await apiFetch<AdminCourseDetail>(
      `/admin/courses/${selectedCourse.id}/members`,
      {
        method: "PUT",
        body: JSON.stringify({
          user_id: courseMemberUserId.trim(),
          role: courseMemberRole,
        }),
      },
    );
    setSelectedCourse(updated);
    setCourseMemberUserId("");
    await loadResources();
  }

  async function removeCourseMember(userId: string) {
    if (!selectedCourse) return;
    const updated = await apiFetch<AdminCourseDetail>(
      `/admin/courses/${selectedCourse.id}/members/${userId}`,
      { method: "DELETE" },
    );
    setSelectedCourse(updated);
    await loadResources();
  }

  async function addCourseDocument() {
    if (!selectedCourse || !courseDocumentId.trim()) return;
    const updated = await apiFetch<AdminCourseDetail>(
      `/admin/courses/${selectedCourse.id}/documents`,
      {
        method: "POST",
        body: JSON.stringify({ doc_id: courseDocumentId.trim() }),
      },
    );
    setSelectedCourse(updated);
    setCourseDocumentId("");
    await loadResources();
  }

  async function removeCourseDocument(docId: string) {
    if (!selectedCourse) return;
    const updated = await apiFetch<AdminCourseDetail>(
      `/admin/courses/${selectedCourse.id}/documents/${docId}`,
      { method: "DELETE" },
    );
    setSelectedCourse(updated);
    await loadResources();
  }

  async function saveConfig() {
    setConfigMessage("");
    setError("");
    const payload = JSON.parse(configText) as Record<string, unknown>;
    const next = await apiFetch<Record<string, unknown>>("/admin/config", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    setConfigText(JSON.stringify(next, null, 2));
    setConfigMessage("設定已更新");
  }

  function handleError(err: unknown) {
    setError(
      err instanceof ApiError || err instanceof Error
        ? err.message
        : "操作失敗",
    );
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">管理後台</h1>
          <p className="mt-1 text-sm text-zinc-500">
            使用者、配額、成本、可靠性與稽核紀錄
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm hover:bg-zinc-50"
            onClick={() => {
              setAdminTab("users");
              setCreateOpen((value) => !value);
            }}
          >
            <UserPlus size={16} />
            新增使用者
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm hover:bg-zinc-50"
            onClick={() => loadAll().catch(handleError)}
          >
            <RefreshCw size={16} />
            重新整理
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}
      {message && (
        <div className="mb-4 rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-700">
          {message}
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[220px_minmax(0,1fr)]">
        <AdminNav active={adminTab} onChange={setAdminTab} />
        <div className="min-w-0">
          {adminTab === "overview" && (
            <>
              <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <Stat label="使用者" value={stats?.users ?? 0} />
                <Stat label="文件" value={stats?.documents ?? 0} />
                <Stat label="Tokens" value={stats?.tokens_used ?? 0} />
                <Stat label="今日 USD" value={cost?.today.total_usd ?? 0} />
                <Stat
                  label="本月 USD"
                  value={cost?.this_month.total_usd ?? 0}
                />
              </div>
              <div className="mb-6 grid gap-4 lg:grid-cols-2">
                <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
                  <h2 className="mb-4 font-semibold">Feature 成本</h2>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={featureRows}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="feature" />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="total_usd" fill="#4f46e5" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </section>
                <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
                  <h2 className="mb-3 font-semibold">可靠性</h2>
                  <div className="mb-4 text-sm text-zinc-600">
                    近 7 天 fallback：{reliability?.fallback_count_7d ?? 0}
                  </div>
                  <div className="space-y-2">
                    {(reliability?.events ?? []).slice(0, 8).map((event) => (
                      <div
                        key={event.id}
                        className="rounded-md bg-zinc-50 p-3 text-xs text-zinc-600"
                      >
                        {shortDate(event.created_at)} ·{" "}
                        {String(event.detail.reason ?? "unknown")} ·{" "}
                        {String(event.detail.model ?? "")}
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            </>
          )}

          {adminTab === "users" && createOpen && (
            <section className="mb-6 rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 font-semibold">新增使用者</h2>
              <form
                className="grid gap-3 md:grid-cols-3 xl:grid-cols-6"
                onSubmit={(event) => createUser(event).catch(handleError)}
              >
                <Input
                  label="帳號"
                  value={createForm.username}
                  onChange={(value) =>
                    setCreateForm((form) => ({ ...form, username: value }))
                  }
                />
                <Input
                  label="Email"
                  type="email"
                  value={createForm.email}
                  onChange={(value) =>
                    setCreateForm((form) => ({ ...form, email: value }))
                  }
                />
                <Input
                  label="初始密碼"
                  type="password"
                  value={createForm.password}
                  onChange={(value) =>
                    setCreateForm((form) => ({ ...form, password: value }))
                  }
                />
                <Select
                  label="角色"
                  value={createForm.role}
                  onChange={(value) =>
                    setCreateForm((form) => ({
                      ...form,
                      role: value as "student" | "teacher" | "admin",
                    }))
                  }
                  options={userRoleOptions}
                />
                <NumberInput
                  label="Token 配額"
                  value={createForm.token_quota}
                  onChange={(value) =>
                    setCreateForm((form) => ({ ...form, token_quota: value }))
                  }
                />
                <button className="mt-6 inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 text-sm font-medium text-white hover:bg-indigo-700">
                  <Plus size={16} />
                  建立
                </button>
              </form>
            </section>
          )}

          {adminTab === "users" && (
            <div className="mb-6 grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(420px,0.65fr)]">
              <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
                <div className="border-b border-zinc-200 p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-center gap-2">
                      <Shield size={18} className="text-zinc-500" />
                      <h2 className="font-semibold">使用者管理</h2>
                      <span className="text-xs text-zinc-500">
                        {totalUsers} 筆
                      </span>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-[1fr_130px_130px]">
                      <label className="relative">
                        <Search
                          className="pointer-events-none absolute left-3 top-2.5 text-zinc-400"
                          size={16}
                        />
                        <input
                          className="w-full rounded-lg border border-zinc-200 py-2 pl-9 pr-3 text-sm"
                          value={q}
                          onChange={(event) => setQ(event.target.value)}
                          placeholder="搜尋帳號或 Email"
                        />
                      </label>
                      <select
                        className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                        value={role}
                        onChange={(event) => setRole(event.target.value)}
                      >
                        <option value="">全部角色</option>
                        <option value="student">學生</option>
                        <option value="teacher">教師</option>
                        <option value="admin">管理員</option>
                      </select>
                      <select
                        className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                        value={active}
                        onChange={(event) => setActive(event.target.value)}
                      >
                        <option value="">全部狀態</option>
                        <option value="1">啟用</option>
                        <option value="0">停用</option>
                      </select>
                    </div>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[900px] text-left text-sm">
                    <thead className="border-b border-zinc-200 bg-zinc-50 text-xs text-zinc-500">
                      <tr>
                        <th className="px-4 py-3 font-medium">使用者</th>
                        <th className="px-4 py-3 font-medium">角色</th>
                        <th className="px-4 py-3 font-medium">狀態</th>
                        <th className="px-4 py-3 font-medium">文件</th>
                        <th className="px-4 py-3 font-medium">本月 Token</th>
                        <th className="px-4 py-3 font-medium">建立時間</th>
                        <th className="px-4 py-3 font-medium">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                      {users.map((user) => (
                        <tr
                          key={user.id}
                          className={
                            selected?.id === user.id
                              ? "bg-indigo-50/60"
                              : "hover:bg-zinc-50"
                          }
                        >
                          <td className="px-4 py-3">
                            <button
                              className="text-left"
                              onClick={() =>
                                selectUser(user.id).catch(handleError)
                              }
                            >
                              <div className="font-medium text-zinc-900">
                                {user.username}
                              </div>
                              <div className="text-xs text-zinc-500">
                                {user.email}
                              </div>
                            </button>
                          </td>
                          <td className="px-4 py-3">
                            {userRoleLabel(user.role)}
                          </td>
                          <td className="px-4 py-3">
                            <StatusBadge active={user.is_active} />
                          </td>
                          <td className="px-4 py-3">
                            {user.document_count} ·{" "}
                            {formatBytes(user.storage_bytes)}
                          </td>
                          <td className="px-4 py-3">
                            <div>
                              {formatNumber(user.token_used_this_month)} /{" "}
                              {formatNumber(user.token_quota)}
                            </div>
                            <div className="mt-1 h-1.5 rounded-full bg-zinc-100">
                              <div
                                className={quotaBarClass(user.quota_status)}
                                style={{
                                  width: `${Math.min(100, user.quota_percent)}%`,
                                }}
                              />
                            </div>
                          </td>
                          <td className="px-4 py-3 text-xs text-zinc-500">
                            {shortDate(user.created_at)}
                          </td>
                          <td className="px-4 py-3">
                            <button
                              className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs hover:bg-zinc-50"
                              onClick={() =>
                                toggleActive(user).catch(handleError)
                              }
                            >
                              {user.is_active ? (
                                <Ban size={14} />
                              ) : (
                                <CheckCircle2 size={14} />
                              )}
                              {user.is_active ? "停用" : "啟用"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
                {selected ? (
                  <div>
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <div>
                        <h2 className="font-semibold">{selected.username}</h2>
                        <p className="mt-1 text-xs text-zinc-500">
                          {selected.id}
                        </p>
                      </div>
                      <StatusBadge active={selected.is_active} />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Input
                        label="帳號"
                        value={selected.username}
                        onChange={(value) =>
                          setSelected((user) =>
                            user ? { ...user, username: value } : user,
                          )
                        }
                      />
                      <Input
                        label="Email"
                        type="email"
                        value={selected.email}
                        onChange={(value) =>
                          setSelected((user) =>
                            user ? { ...user, email: value } : user,
                          )
                        }
                      />
                      <Select
                        label="角色"
                        value={selected.role}
                        onChange={(value) =>
                          setSelected((user) =>
                            user
                              ? {
                                  ...user,
                                  role: value as
                                    | "student"
                                    | "teacher"
                                    | "admin",
                                }
                              : user,
                          )
                        }
                        options={userRoleOptions}
                      />
                      <Select
                        label="狀態"
                        value={String(selected.is_active)}
                        onChange={(value) =>
                          setSelected((user) =>
                            user ? { ...user, is_active: Number(value) } : user,
                          )
                        }
                        options={[
                          ["1", "啟用"],
                          ["0", "停用"],
                        ]}
                      />
                      <NumberInput
                        label="上傳配額 MB"
                        value={selected.quota_mb}
                        onChange={(value) =>
                          setSelected((user) =>
                            user ? { ...user, quota_mb: value } : user,
                          )
                        }
                      />
                      <NumberInput
                        label="Token 月配額"
                        value={selected.token_quota}
                        onChange={(value) =>
                          setSelected((user) =>
                            user ? { ...user, token_quota: value } : user,
                          )
                        }
                      />
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                        onClick={() => saveSelected().catch(handleError)}
                      >
                        <Save size={16} />
                        儲存
                      </button>
                      <button
                        className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                        onClick={() => forcePurge().catch(handleError)}
                      >
                        <Trash2 size={16} />
                        永久清除
                      </button>
                    </div>

                    <div className="mt-6 border-t border-zinc-200 pt-4">
                      <h3 className="mb-3 text-sm font-semibold">重設密碼</h3>
                      <div className="flex gap-2">
                        <input
                          className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                          type="password"
                          value={password}
                          onChange={(event) => setPassword(event.target.value)}
                          placeholder="至少 8 個字元"
                        />
                        <button
                          className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50"
                          onClick={() => resetPassword().catch(handleError)}
                          disabled={password.length < 8}
                        >
                          <KeyRound size={16} />
                          重設
                        </button>
                      </div>
                    </div>

                    <div className="mt-6 grid gap-3 sm:grid-cols-3">
                      <MiniStat label="文件" value={selected.document_count} />
                      <MiniStat
                        label="容量"
                        value={formatBytes(selected.storage_bytes)}
                      />
                      <MiniStat
                        label="Token %"
                        value={`${selected.usage.quota_percent}%`}
                      />
                    </div>
                    <div className="mt-6 h-56">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={selected.usage.daily_series}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" hide />
                          <YAxis />
                          <Tooltip />
                          <Line
                            type="monotone"
                            dataKey="tokens"
                            stroke="#4f46e5"
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="mt-4 h-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={selectedFeatureRows}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="feature" />
                          <YAxis />
                          <Tooltip />
                          <Bar dataKey="tokens" fill="#16a34a" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                ) : (
                  <div className="flex min-h-80 items-center justify-center text-sm text-zinc-500">
                    選擇一位使用者查看詳情
                  </div>
                )}
              </section>
            </div>
          )}

          {adminTab === "resources" && (
            <section className="mb-6 rounded-lg border border-zinc-200 bg-white shadow-sm">
              <div className="flex flex-col gap-3 border-b border-zinc-200 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="font-semibold">全域資源管理</h2>
                  <p className="mt-1 text-sm text-zinc-500">
                    管理員可跨使用者管理文件、對話與課程
                  </p>
                </div>
                <button
                  className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50"
                  onClick={() => loadResources().catch(handleError)}
                >
                  <RefreshCw size={16} />
                  更新資源
                </button>
              </div>
              <div className="grid gap-0 xl:grid-cols-2">
                <ResourcePanel title="文件" icon={<FileText size={17} />}>
                  {adminDocuments.map((doc) => (
                    <div
                      key={doc.id}
                      className="border-b border-zinc-100 p-3 text-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">
                            {doc.filename}
                          </div>
                          <div className="mt-1 text-xs text-zinc-500">
                            {doc.username} · {formatBytes(doc.file_size)} ·{" "}
                            {doc.status}
                          </div>
                          {doc.error_msg && (
                            <div className="mt-1 line-clamp-2 text-xs text-red-600">
                              {doc.error_msg}
                            </div>
                          )}
                        </div>
                        <button
                          className="shrink-0 rounded-md border border-red-200 p-1 text-red-600 hover:bg-red-50"
                          onClick={() =>
                            deleteAdminDocument(doc).catch(handleError)
                          }
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                  {adminDocuments.length === 0 && <EmptyResource />}
                </ResourcePanel>

                <ResourcePanel title="對話" icon={<MessageSquare size={17} />}>
                  {adminChats.map((session) => (
                    <div
                      key={session.id}
                      className="border-b border-zinc-100 p-3 text-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <button
                          className="min-w-0 text-left"
                          onClick={() =>
                            openAdminChat(session.id).catch(handleError)
                          }
                        >
                          <div className="truncate font-medium">
                            {session.title ?? "未命名對話"}
                          </div>
                          <div className="mt-1 text-xs text-zinc-500">
                            {session.username} · {session.mode} ·{" "}
                            {session.message_count} 則
                          </div>
                        </button>
                        <button
                          className="shrink-0 rounded-md border border-red-200 p-1 text-red-600 hover:bg-red-50"
                          onClick={() =>
                            deleteAdminChat(session).catch(handleError)
                          }
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                  {selectedChat && (
                    <div className="max-h-80 overflow-y-auto border-t border-zinc-200 bg-zinc-50 p-3">
                      <div className="mb-2 text-xs font-semibold text-zinc-500">
                        對話內容
                      </div>
                      {selectedChat.messages.map((message) => (
                        <div
                          key={message.id}
                          className="mb-2 rounded-md bg-white p-2 text-xs"
                        >
                          <div className="mb-1 font-medium">
                            {message.role} · {shortDate(message.created_at)}
                          </div>
                          <div className="line-clamp-4 text-zinc-600">
                            {message.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  {adminChats.length === 0 && <EmptyResource />}
                </ResourcePanel>
              </div>
            </section>
          )}

          {adminTab === "courses" && (
            <section className="mb-6 rounded-lg border border-zinc-200 bg-white shadow-sm">
              <div className="flex flex-col gap-3 border-b border-zinc-200 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="font-semibold">課程管理</h2>
                  <p className="mt-1 text-sm text-zinc-500">
                    管理課程、成員與共享教材
                  </p>
                </div>
                <button
                  className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50"
                  onClick={() => loadResources().catch(handleError)}
                >
                  <RefreshCw size={16} />
                  更新課程
                </button>
              </div>
              <ResourcePanel title="課程" icon={<BookOpen size={17} />}>
                {adminCourses.map((course) => (
                  <div
                    key={course.id}
                    className="border-b border-zinc-100 p-3 text-sm"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <button
                        className="min-w-0 text-left"
                        onClick={() =>
                          openAdminCourse(course.id).catch(handleError)
                        }
                      >
                        <div className="truncate font-medium">
                          {course.title}
                        </div>
                        <div className="mt-1 text-xs text-zinc-500">
                          {course.owner_username} · {course.member_count} 人 ·{" "}
                          {course.document_count} 文件
                        </div>
                      </button>
                      <button
                        className="shrink-0 rounded-md border border-red-200 p-1 text-red-600 hover:bg-red-50"
                        onClick={() =>
                          deleteAdminCourse(course).catch(handleError)
                        }
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
                {selectedCourse && (
                  <div className="border-t border-zinc-200 bg-zinc-50 p-3">
                    <div className="grid gap-2">
                      <Input
                        label="課程名稱"
                        value={selectedCourse.title}
                        onChange={(value) =>
                          setSelectedCourse((course) =>
                            course ? { ...course, title: value } : course,
                          )
                        }
                      />
                      <Input
                        label="描述"
                        value={selectedCourse.description ?? ""}
                        onChange={(value) =>
                          setSelectedCourse((course) =>
                            course ? { ...course, description: value } : course,
                          )
                        }
                      />
                      <Select
                        label="狀態"
                        value={String(selectedCourse.is_active)}
                        onChange={(value) =>
                          setSelectedCourse((course) =>
                            course
                              ? { ...course, is_active: Number(value) }
                              : course,
                          )
                        }
                        options={[
                          ["1", "啟用"],
                          ["0", "停用"],
                        ]}
                      />
                      <button
                        className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                        onClick={() => saveAdminCourse().catch(handleError)}
                      >
                        <Save size={16} />
                        儲存課程
                      </button>
                    </div>
                    <div className="mt-4">
                      <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-zinc-500">
                        <Users size={14} />
                        成員
                      </div>
                      <div className="mb-2 grid gap-2 sm:grid-cols-[1fr_120px_auto]">
                        <input
                          className="rounded-lg border border-zinc-200 px-3 py-2 text-xs"
                          value={courseMemberUserId}
                          onChange={(event) =>
                            setCourseMemberUserId(event.target.value)
                          }
                          placeholder="user_id"
                        />
                        <select
                          className="rounded-lg border border-zinc-200 px-2 py-2 text-xs"
                          value={courseMemberRole}
                          onChange={(event) =>
                            setCourseMemberRole(
                              event.target.value as
                                | "student"
                                | "ta"
                                | "instructor",
                            )
                          }
                        >
                          <option value="student">student</option>
                          <option value="ta">ta</option>
                          <option value="instructor">instructor</option>
                        </select>
                        <button
                          className="rounded-lg border border-zinc-200 px-3 py-2 text-xs hover:bg-white"
                          onClick={() => addCourseMember().catch(handleError)}
                        >
                          加入
                        </button>
                      </div>
                      {selectedCourse.members.map((member) => (
                        <div
                          key={member.user_id}
                          className="flex items-center justify-between rounded-md bg-white px-2 py-1 text-xs"
                        >
                          <span className="truncate">
                            {member.username} · {member.role}
                          </span>
                          {member.user_id !== selectedCourse.owner_id && (
                            <button
                              className="text-red-600"
                              onClick={() =>
                                removeCourseMember(member.user_id).catch(
                                  handleError,
                                )
                              }
                            >
                              移除
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="mt-4">
                      <div className="mb-2 text-xs font-semibold text-zinc-500">
                        教材
                      </div>
                      <div className="mb-2 flex gap-2">
                        <select
                          className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-xs"
                          value={courseDocumentId}
                          onChange={(event) =>
                            setCourseDocumentId(event.target.value)
                          }
                        >
                          <option value="">選擇 ready 文件</option>
                          {adminDocuments
                            .filter((doc) => doc.status === "ready")
                            .map((doc) => (
                              <option key={doc.id} value={doc.id}>
                                {doc.filename} · {doc.username}
                              </option>
                            ))}
                        </select>
                        <button
                          className="rounded-lg border border-zinc-200 px-3 py-2 text-xs hover:bg-white"
                          onClick={() => addCourseDocument().catch(handleError)}
                        >
                          加入
                        </button>
                      </div>
                      {selectedCourse.documents.map((doc) => (
                        <div
                          key={doc.id}
                          className="flex items-center justify-between rounded-md bg-white px-2 py-1 text-xs"
                        >
                          <span className="truncate">
                            {doc.filename} · {doc.username} · {doc.status}
                          </span>
                          <button
                            className="text-red-600"
                            onClick={() =>
                              removeCourseDocument(doc.id).catch(handleError)
                            }
                          >
                            移除
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {adminCourses.length === 0 && <EmptyResource />}
              </ResourcePanel>
            </section>
          )}

          {adminTab === "settings" && (
            <section className="mb-6 rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 font-semibold">LLM / Fallback 設定</h2>
              <textarea
                className="min-h-72 w-full rounded-lg border border-zinc-200 px-3 py-2 font-mono text-xs"
                value={configText}
                onChange={(event) => setConfigText(event.target.value)}
              />
              <div className="mt-3 flex items-center gap-3">
                <button
                  className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                  onClick={() => saveConfig().catch(handleError)}
                >
                  儲存設定
                </button>
                {configMessage && (
                  <span className="text-sm text-indigo-700">
                    {configMessage}
                  </span>
                )}
              </div>
            </section>
          )}

          {adminTab === "audit" && (
            <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
              <div className="border-b border-zinc-200 px-5 py-4">
                <h2 className="font-semibold">Audit logs</h2>
              </div>
              <div className="divide-y divide-zinc-100">
                {auditLogs.map((log) => (
                  <div
                    key={String(log.id)}
                    className="grid gap-2 px-5 py-3 text-xs sm:grid-cols-[170px_180px_1fr]"
                  >
                    <div className="text-zinc-500">
                      {shortDate(String(log.created_at))}
                    </div>
                    <div className="font-medium">{String(log.action)}</div>
                    <div className="truncate text-zinc-500">
                      {String(log.resource ?? "")}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="text-sm text-zinc-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{formatNumber(value)}</div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-zinc-50 p-3">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}

function AdminNav({
  active,
  onChange,
}: {
  active: AdminTab;
  onChange: (tab: AdminTab) => void;
}) {
  const userArea: Array<[AdminTab, string, ReactNode]> = [
    ["overview", "概覽", <LayoutDashboard size={16} />],
    ["users", "使用者", <Users size={16} />],
  ];
  const adminArea: Array<[AdminTab, string, ReactNode]> = [
    ["resources", "資源", <FileText size={16} />],
    ["courses", "課程", <BookOpen size={16} />],
    ["settings", "模型設定", <SlidersHorizontal size={16} />],
    ["audit", "稽核", <Shield size={16} />],
  ];
  return (
    <aside className="h-fit rounded-lg border border-zinc-200 bg-white p-3 shadow-sm">
      <NavGroup
        title="User Area"
        items={userArea}
        active={active}
        onChange={onChange}
      />
      <div className="my-3 border-t border-zinc-100" />
      <NavGroup
        title="Admin Area"
        items={adminArea}
        active={active}
        onChange={onChange}
      />
    </aside>
  );
}

function NavGroup({
  title,
  items,
  active,
  onChange,
}: {
  title: string;
  items: Array<[AdminTab, string, ReactNode]>;
  active: AdminTab;
  onChange: (tab: AdminTab) => void;
}) {
  return (
    <div>
      <div className="mb-2 px-2 text-xs font-semibold uppercase text-zinc-400">
        {title}
      </div>
      <div className="space-y-1">
        {items.map(([tab, label, icon]) => (
          <button
            key={tab}
            className={
              tab === active
                ? "flex w-full items-center gap-2 rounded-md bg-indigo-50 px-3 py-2 text-left text-sm font-medium text-indigo-700"
                : "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50"
            }
            onClick={() => onChange(tab)}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function ResourcePanel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="min-h-80 border-b border-zinc-200 xl:border-b-0 xl:border-r xl:last:border-r-0">
      <div className="flex items-center gap-2 border-b border-zinc-200 px-4 py-3 text-sm font-semibold">
        <span className="text-zinc-500">{icon}</span>
        {title}
      </div>
      <div>{children}</div>
    </div>
  );
}

function EmptyResource() {
  return <div className="p-6 text-sm text-zinc-500">目前沒有資料</div>;
}

function Input({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-zinc-500">
        {label}
      </span>
      <input
        className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function NumberInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-zinc-500">
        {label}
      </span>
      <input
        className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
        type="number"
        min={1}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: [string, string][];
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-zinc-500">
        {label}
      </span>
      <select
        className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </label>
  );
}

function StatusBadge({ active }: { active: number }) {
  return (
    <span
      className={
        active
          ? "rounded-full bg-green-50 px-2 py-1 text-xs text-green-700"
          : "rounded-full bg-zinc-100 px-2 py-1 text-xs text-zinc-500"
      }
    >
      {active ? "啟用" : "停用"}
    </span>
  );
}

function quotaBarClass(statusValue: AdminUser["quota_status"]) {
  const color =
    statusValue === "exceeded"
      ? "bg-red-600"
      : statusValue === "warning"
        ? "bg-amber-500"
        : "bg-indigo-600";
  return `h-1.5 rounded-full ${color}`;
}

const userRoleOptions: [string, string][] = [
  ["student", "學生"],
  ["teacher", "教師"],
  ["admin", "管理員"],
];

function userRoleLabel(role: string) {
  if (role === "admin") return "管理員";
  if (role === "teacher") return "教師";
  return "學生";
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function formatNumber(value: number) {
  if (Number.isInteger(value)) return value.toLocaleString();
  return value.toFixed(4).replace(/\.?0+$/, "");
}

function shortDate(value: string) {
  return value ? value.slice(0, 19).replace("T", " ") : "";
}
