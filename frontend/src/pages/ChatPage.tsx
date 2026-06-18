import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  HelpCircle,
  Info,
  Lightbulb,
  Loader2,
  NotebookPen,
  MessageSquarePlus,
  Send,
  StopCircle,
  Trash2,
} from "lucide-react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { AIGeneratedBadge } from "../components/app/AIGeneratedBadge";
import { LoadingButton } from "../components/app/LoadingButton";
import { MarkdownContent } from "../components/app/MarkdownContent";
import {
  apiFetch,
  ChatMessage,
  ChatSession,
  Citation,
  CourseItem,
  DocumentItem,
} from "../lib/api";
import { streamFetch } from "../lib/stream";
import { useAuthStore } from "../store/auth";

const modeDescriptions: Record<string, { title: string; text: string }> = {
  enhanced: {
    title: "增強模式",
    text: "優先根據教材回答，教材不足時會補充一般背景知識，適合探索與整理概念。",
  },
  strict: {
    title: "嚴格模式",
    text: "只根據引用教材回答；資料不足會直接說明找不到依據，適合考前複習與查證。",
  },
  socratic: {
    title: "蘇格拉底模式",
    text: "用反問與提示引導你自己推理答案，適合練習理解、口試或主動回想。",
  },
};

const starterPrompts = [
  "請先用 5 個重點整理這份教材的核心概念。",
  "請列出我最需要先理解的名詞與定義，並用簡短例子說明。",
  "請根據教材幫我設計 3 題自我檢核問題，先不要直接給答案。",
  "請指出這份教材容易混淆的地方，並用表格比較差異。",
];

export function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<CourseItem | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [courseId, setCourseId] = useState<string>("");
  const [mode, setMode] = useState("enhanced");
  const [streaming, setStreaming] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const [sending, setSending] = useState(false);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(
    null,
  );
  const [helpLoading, setHelpLoading] = useState(false);
  const [helpMessage, setHelpMessage] = useState("");
  const [savingNoteKey, setSavingNoteKey] = useState<string | null>(null);
  const [savedNoteKeys, setSavedNoteKeys] = useState<Set<string>>(new Set());
  const [aborter, setAborter] = useState<AbortController | null>(null);
  const user = useAuthStore((state) => state.user);
  const aiDisabled = user?.quota_status === "exceeded";
  const { sessionId: routeSessionId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeId),
    [sessions, activeId],
  );
  const helpCourseId = activeSession?.course_id ?? "";
  const scopeDocuments = courseId
    ? (selectedCourse?.documents ?? []).filter((doc) => doc.status === "ready")
    : documents.filter((doc) => doc.status === "ready");
  const scopeDocumentIds = scopeDocuments.map((doc) => doc.id);
  const availableSelectedDocs = selectedDocs.filter((docId) =>
    scopeDocumentIds.includes(docId),
  );
  const allScopeDocumentsSelected =
    scopeDocumentIds.length > 0 &&
    scopeDocumentIds.every((docId) => availableSelectedDocs.includes(docId));

  useEffect(() => {
    loadSessions().catch(() => undefined);
    apiFetch<DocumentItem[]>("/documents")
      .then(setDocuments)
      .catch(() => setDocuments([]));
    apiFetch<CourseItem[]>("/courses")
      .then(setCourses)
      .catch(() => setCourses([]));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const doc = params.get("doc");
    const docs = params.get("docs");
    const course = params.get("course");
    const nextMode = params.get("mode");
    if (doc || docs || course) {
      setActiveId(null);
      setMessages([]);
    }
    if (course) setCourseId(course);
    if (docs)
      setSelectedDocs(
        docs
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      );
    else if (doc) setSelectedDocs([doc]);
    if (nextMode && modeDescriptions[nextMode]) setMode(nextMode);
  }, [location.search]);

  useEffect(() => {
    if (routeSessionId && routeSessionId !== activeId) {
      openSession(routeSessionId, false).catch(() => undefined);
    }
  }, [routeSessionId]);

  useEffect(() => {
    if (!courseId) {
      setSelectedCourse(null);
      if (documents.length > 0) {
        setSelectedDocs((prev) =>
          prev.filter((docId) => documents.some((doc) => doc.id === docId)),
        );
      }
      return;
    }
    apiFetch<CourseItem>(`/courses/${courseId}`)
      .then((course) => {
        setSelectedCourse(course);
        const allowed = new Set(
          (course.documents ?? [])
            .filter((doc) => doc.status === "ready")
            .map((doc) => doc.id),
        );
        setSelectedDocs((prev) => prev.filter((docId) => allowed.has(docId)));
      })
      .catch(() => {
        setSelectedCourse(null);
        setSelectedDocs([]);
      });
  }, [courseId, documents]);

  async function loadSessions() {
    const data = await apiFetch<ChatSession[]>("/chat/sessions");
    setSessions(data);
    if (
      !activeId &&
      !routeSessionId &&
      data[0] &&
      !hasDraftChatScope(location.search)
    ) {
      await openSession(data[0].id);
    }
  }

  async function openSession(id: string, pushUrl = true) {
    const detail = await apiFetch<ChatSession>(`/chat/sessions/${id}`);
    setActiveId(id);
    setMessages(detail.messages ?? []);
    setMode(detail.mode);
    setCourseId(detail.course_id ?? "");
    setSelectedDocs(detail.doc_ids);
    if (pushUrl) navigate(`/chat/${id}`);
  }

  async function createSession() {
    setCreatingSession(true);
    try {
      const session = await apiFetch<ChatSession>("/chat/sessions", {
        method: "POST",
        body: JSON.stringify({
          doc_ids: availableSelectedDocs,
          mode,
          course_id: courseId || null,
        }),
      });
      setSessions((prev) => [session, ...prev]);
      setActiveId(session.id);
      setMessages([]);
      navigate(`/chat/${session.id}`);
    } finally {
      setCreatingSession(false);
    }
  }

  async function deleteSession(sessionId: string) {
    if (deletingSessionId) return;
    setDeletingSessionId(sessionId);
    try {
      if (sessionId === activeId) {
        aborter?.abort();
      }
      await apiFetch(`/chat/sessions/${sessionId}`, { method: "DELETE" });
      setSessions((prev) => prev.filter((session) => session.id !== sessionId));
      if (sessionId === activeId) {
        setActiveId(null);
        setMessages([]);
        navigate("/chat");
      }
    } finally {
      setDeletingSessionId(null);
    }
  }

  async function sendQuestion(rawQuestion: string) {
    const question = rawQuestion.trim();
    if (!question || streaming || sending || aiDisabled) return;
    setSending(true);
    let sessionId = activeId;
    let assistant = "";
    let citations: Citation[] = [];
    try {
      if (!sessionId) {
        const session = await apiFetch<ChatSession>("/chat/sessions", {
          method: "POST",
          body: JSON.stringify({
            doc_ids: availableSelectedDocs,
            mode,
            course_id: courseId || null,
          }),
        });
        setSessions((prev) => [session, ...prev]);
        sessionId = session.id;
        setActiveId(session.id);
        navigate(`/chat/${session.id}`);
      }
      setInput("");
      setMessages((prev) => [
        ...prev,
        { role: "user", content: question },
        { role: "assistant", content: "" },
      ]);
      const controller = new AbortController();
      setAborter(controller);
      setSending(false);
      setStreaming(true);
      for await (const event of streamFetch(
        `/chat/sessions/${sessionId}/message`,
        { content: question },
        controller.signal,
      )) {
        if (event.type === "chunk") {
          assistant += event.content;
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              role: "assistant",
              content: assistant,
              citations,
            };
            return next;
          });
        } else if (event.type === "citations") {
          citations = event.data;
        } else if (event.type === "error") {
          assistant += `\n\n[錯誤：${event.message}]`;
        }
      }
    } finally {
      setMessages((prev) => {
        const next = [...prev];
        if (next.length > 0 && next[next.length - 1].role === "assistant") {
          next[next.length - 1] = {
            role: "assistant",
            content: assistant,
            citations,
          };
        }
        return next;
      });
      setStreaming(false);
      setSending(false);
      setAborter(null);
      loadSessions().catch(() => undefined);
    }
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    await sendQuestion(input);
  }

  async function createHelpRequest() {
    if (!activeId || !helpCourseId) return;
    const latestUserMessage = [...messages]
      .reverse()
      .find((message) => message.role === "user");
    const context = messages
      .slice(-6)
      .map(
        (message) =>
          `${message.role === "user" ? "學生" : "AI"}：${message.content}`,
      )
      .join("\n\n");
    setHelpLoading(true);
    setHelpMessage("");
    try {
      await apiFetch(`/courses/${helpCourseId}/help-requests`, {
        method: "POST",
        body: JSON.stringify({
          title:
            latestUserMessage?.content.slice(0, 120) ||
            activeSession?.title ||
            "課程對話求助",
          content: context || latestUserMessage?.content || null,
          session_id: activeId,
          priority: "normal",
        }),
      });
      setHelpMessage("已送出求助");
    } catch (err) {
      setHelpMessage(err instanceof Error ? err.message : "求助送出失敗");
    } finally {
      setHelpLoading(false);
    }
  }

  async function saveMessageToNote(message: ChatMessage, index: number) {
    if (!message.content.trim()) return;
    const key = `chat-${activeId ?? "draft"}-${index}`;
    const firstCitation = message.citations?.[0];
    setSavingNoteKey(key);
    try {
      await apiFetch("/notes", {
        method: "POST",
        body: JSON.stringify({
          content: message.content,
          session_id: activeId,
          doc_id: firstCitation?.doc_id ?? null,
          source_page: firstCitation?.page ?? null,
          source_type: "chat",
        }),
      });
      setSavedNoteKeys((current) => new Set(current).add(key));
    } finally {
      setSavingNoteKey(null);
    }
  }

  return (
    <div className="grid min-h-[calc(100vh-40px)] gap-4 lg:grid-cols-[280px_1fr]">
      <aside className="rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="border-b border-zinc-200 p-4">
          <LoadingButton
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            onClick={createSession}
            loading={creatingSession}
            loadingText="建立中"
            icon={<MessageSquarePlus size={16} />}
          >
            新對話
          </LoadingButton>
        </div>
        <div className="border-b border-zinc-200 p-4">
          <label className="mb-2 block text-xs font-medium text-zinc-500">
            模式
          </label>
          <select
            className="mb-3 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            value={mode}
            onChange={(event) => setMode(event.target.value)}
          >
            <option value="enhanced">增強</option>
            <option value="strict">嚴格</option>
            <option value="socratic">蘇格拉底</option>
          </select>
          <div className="mb-3 flex gap-2 rounded-md bg-zinc-50 px-3 py-2 text-xs leading-5 text-zinc-600">
            <Info size={14} className="mt-0.5 shrink-0 text-zinc-400" />
            <div>
              <div className="font-medium text-zinc-700">
                {modeDescriptions[mode].title}
              </div>
              <div>{modeDescriptions[mode].text}</div>
            </div>
          </div>
          <label className="mb-2 block text-xs font-medium text-zinc-500">
            範圍
          </label>
          <select
            className="mb-3 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            value={courseId}
            onChange={(event) => {
              setCourseId(event.target.value);
              setSelectedDocs([]);
            }}
          >
            <option value="">個人文件</option>
            {courses.map((course) => (
              <option key={course.id} value={course.id}>
                {course.title}
              </option>
            ))}
          </select>
          <div className="space-y-2">
            {scopeDocuments.length > 0 && (
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                  onClick={() => setSelectedDocs(scopeDocumentIds)}
                >
                  全選文件
                </button>
                <button
                  type="button"
                  className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                  onClick={() => setSelectedDocs([])}
                >
                  清空
                </button>
                <span className="text-xs text-zinc-500">
                  已選 {selectedDocs.length} / {scopeDocuments.length}
                </span>
                {allScopeDocumentsSelected && (
                  <span className="text-xs text-indigo-700">已全選</span>
                )}
              </div>
            )}
            {scopeDocuments.map((doc) => (
              <label key={doc.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selectedDocs.includes(doc.id)}
                  onChange={(event) => {
                    setSelectedDocs((prev) =>
                      event.target.checked
                        ? [...prev, doc.id]
                        : prev.filter((item) => item !== doc.id),
                    );
                  }}
                />
                <span className="truncate">{doc.filename}</span>
              </label>
            ))}
            {scopeDocuments.length === 0 && (
              <div className="rounded-md bg-zinc-50 px-3 py-2 text-xs text-zinc-500">
                {courseId ? "此課程尚無可用教材" : "尚無 ready 文件"}
              </div>
            )}
            {courseId &&
              scopeDocuments.length > 0 &&
              selectedDocs.length === 0 && (
                <div className="text-xs text-zinc-500">
                  未勾選時會搜尋此課程全部教材
                </div>
              )}
          </div>
        </div>
        <div className="max-h-[55vh] overflow-y-auto p-2 scrollbar-thin">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={[
                "mb-1 flex items-center rounded-lg",
                session.id === activeId
                  ? "bg-indigo-50 text-indigo-700"
                  : "hover:bg-zinc-100",
              ].join(" ")}
            >
              <button
                className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm"
                onClick={() => openSession(session.id)}
              >
                {session.title || "新的對話"}
              </button>
              <button
                type="button"
                className="mr-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-400 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:text-zinc-300"
                onClick={() => deleteSession(session.id)}
                disabled={deletingSessionId !== null}
                aria-label={`刪除對話 ${session.title || "新的對話"}`}
                aria-busy={deletingSessionId === session.id}
                title="刪除對話"
              >
                {deletingSessionId === session.id ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Trash2 size={14} />
                )}
              </button>
            </div>
          ))}
        </div>
      </aside>
      <section className="flex min-h-[calc(100vh-40px)] flex-col rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="border-b border-zinc-200 px-5 py-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="font-semibold">
                {activeSession?.title || "RAG 對話"}
              </h1>
              {activeSession?.course_id && (
                <div className="mt-1 text-xs text-zinc-500">
                  課程對話：
                  {courses.find(
                    (course) => course.id === activeSession.course_id,
                  )?.title ?? activeSession.course_id}
                </div>
              )}
            </div>
            {activeId && helpCourseId && (
              <div className="flex items-center gap-2">
                {helpMessage && (
                  <span className="text-xs text-zinc-500">{helpMessage}</span>
                )}
                <LoadingButton
                  className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-xs text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100"
                  onClick={createHelpRequest}
                  loading={helpLoading}
                  loadingText="送出中"
                  icon={<HelpCircle size={14} />}
                >
                  求助
                </LoadingButton>
              </div>
            )}
          </div>
        </div>
        <div
          className="flex-1 space-y-4 overflow-y-auto p-5 scrollbar-thin"
          aria-live="polite"
          aria-busy={streaming}
        >
          {messages.length === 0 && !streaming && (
            <div className="rounded-lg border border-dashed border-zinc-200 bg-zinc-50 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-700">
                <Lightbulb size={16} className="text-indigo-600" />
                快速開始
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-left text-sm leading-6 text-zinc-700 hover:border-indigo-200 hover:bg-indigo-50 disabled:cursor-not-allowed disabled:bg-zinc-100 disabled:text-zinc-400"
                    onClick={() => sendQuestion(prompt)}
                    disabled={sending || aiDisabled}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((message, index) => (
            <div
              key={index}
              className={
                message.role === "user"
                  ? "ml-auto max-w-2xl"
                  : "mr-auto max-w-3xl"
              }
            >
              <div
                className={[
                  "rounded-lg px-4 py-3 text-sm leading-7",
                  message.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "border border-zinc-200 bg-zinc-50 text-zinc-900",
                ].join(" ")}
              >
                {message.role === "assistant" ? (
                  <MarkdownContent className="text-sm">
                    {message.content}
                  </MarkdownContent>
                ) : (
                  <div className="whitespace-pre-wrap">{message.content}</div>
                )}
              </div>
              {message.role === "assistant" &&
                activeSession?.mode !== "strict" &&
                message.content && (
                  <AIGeneratedBadge
                    variant="inline"
                    text={
                      activeSession?.mode === "socratic"
                        ? "AI 引導問答，答案由您作答"
                        : "AI 生成回應，請搭配引用驗證"
                    }
                  />
                )}
              {message.role === "assistant" && message.content && (
                <div className="mt-2 flex justify-end">
                  <LoadingButton
                    className="inline-flex items-center gap-1 rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:text-zinc-400"
                    onClick={() => saveMessageToNote(message, index)}
                    loading={
                      savingNoteKey === `chat-${activeId ?? "draft"}-${index}`
                    }
                    loadingText="儲存中"
                    icon={<NotebookPen size={13} />}
                  >
                    {savedNoteKeys.has(`chat-${activeId ?? "draft"}-${index}`)
                      ? "已存筆記"
                      : "存到筆記"}
                  </LoadingButton>
                </div>
              )}
              {message.citations && message.citations.length > 0 && (
                <div className="mt-2 grid gap-2 text-xs text-zinc-500 sm:grid-cols-2">
                  {message.citations.map((citation) => (
                    <Link
                      key={`${citation.doc_id}-${citation.chunk_index}`}
                      to={`/documents/${citation.doc_id}`}
                      className="rounded-lg border border-zinc-200 bg-white px-3 py-2 hover:bg-zinc-50"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-zinc-700">
                          [{citation.index}] {citation.filename} p.
                          {citation.page}
                          {citation.scope === "course" ? " · 課程" : ""}
                        </span>
                        <span className={supportClass(citation.support_status)}>
                          {supportLabel(citation.support_status)}
                        </span>
                      </div>
                      {citation.snippet && (
                        <div className="mt-1 line-clamp-2 leading-5 text-zinc-500">
                          {citation.snippet}
                        </div>
                      )}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        <form onSubmit={sendMessage} className="border-t border-zinc-200 p-4">
          <div className="flex gap-2">
            <label className="sr-only" htmlFor="chat-message-input">
              輸入問題
            </label>
            <input
              id="chat-message-input"
              className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-indigo-600"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="輸入問題"
              disabled={aiDisabled}
            />
            {streaming ? (
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                onClick={() => aborter?.abort()}
              >
                <StopCircle size={16} />
                停止
              </button>
            ) : (
              <button
                disabled={aiDisabled || sending}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                aria-busy={sending}
              >
                {sending ? (
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/50 border-t-white" />
                ) : (
                  <Send size={16} />
                )}
                {sending ? "送出中" : "送出"}
              </button>
            )}
          </div>
        </form>
      </section>
    </div>
  );
}

function hasDraftChatScope(search: string) {
  const params = new URLSearchParams(search);
  return Boolean(
    params.get("doc") || params.get("docs") || params.get("course"),
  );
}

function supportLabel(status?: string) {
  if (status === "supported") return "已支持";
  if (status === "partial") return "部分";
  return "待驗證";
}

function supportClass(status?: string) {
  const base = "shrink-0 rounded-md px-1.5 py-0.5 text-[11px]";
  if (status === "supported") return `${base} bg-emerald-50 text-emerald-700`;
  if (status === "partial") return `${base} bg-amber-50 text-amber-700`;
  return `${base} bg-zinc-100 text-zinc-600`;
}
