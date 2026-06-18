import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Download, Filter, NotebookPen, Pencil } from "lucide-react";
import { useLocation } from "react-router-dom";
import { MarkdownContent } from "../components/app/MarkdownContent";
import { LoadingButton } from "../components/app/LoadingButton";
import {
  BASE_URL,
  apiFetch,
  CourseItem,
  DocumentItem,
  NoteItem,
  refreshToken,
} from "../lib/api";
import { useAuthStore } from "../store/auth";

export function NotesPage() {
  const user = useAuthStore((state) => state.user);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<CourseItem | null>(null);
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [docId, setDocId] = useState("");
  const [courseId, setCourseId] = useState("");
  const [q, setQ] = useState("");
  const [selectedNoteIds, setSelectedNoteIds] = useState<string[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState("");
  const [editingContent, setEditingContent] = useState("");
  const [savingNoteId, setSavingNoteId] = useState("");
  const location = useLocation();
  const scopeDocuments = courseId
    ? (selectedCourse?.documents ?? []).filter((doc) => doc.status === "ready")
    : documents;
  const courseDocIds = useMemo(
    () => new Set(scopeDocuments.map((doc) => doc.id)),
    [scopeDocuments],
  );
  const visibleNotes = courseId
    ? notes.filter((note) => note.doc_id && courseDocIds.has(note.doc_id))
    : notes;

  async function load() {
    const [docs, nextNotes, nextCourses] = await Promise.all([
      apiFetch<DocumentItem[]>("/documents"),
      apiFetch<NoteItem[]>(`/notes${queryString({ doc_id: docId, q })}`),
      apiFetch<CourseItem[]>("/courses").catch(() => []),
    ]);
    setDocuments(docs);
    setNotes(nextNotes);
    setCourses(nextCourses);
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, [docId, q, courseId]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const doc = params.get("doc");
    const course = params.get("course");
    if (doc) setDocId(doc);
    if (course) setCourseId(course);
  }, [location.search]);

  useEffect(() => {
    if (!courseId) {
      setSelectedCourse(null);
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
        setDocId((current) => (current && allowed.has(current) ? current : ""));
      })
      .catch(() => {
        setSelectedCourse(null);
        setDocId("");
      });
  }, [courseId]);

  async function deleteNote(id: string) {
    await apiFetch(`/notes/${id}`, { method: "DELETE" });
    setSelectedNoteIds((current) => current.filter((noteId) => noteId !== id));
    await load();
  }

  function startEditing(note: NoteItem) {
    setEditingNoteId(note.id);
    setEditingContent(note.content);
  }

  function cancelEditing() {
    setEditingNoteId("");
    setEditingContent("");
  }

  async function saveNote(note: NoteItem) {
    if (!editingContent.trim()) return;
    setSavingNoteId(note.id);
    try {
      await apiFetch<NoteItem>(`/notes/${note.id}`, {
        method: "PUT",
        body: JSON.stringify({ content: editingContent }),
      });
      cancelEditing();
      await load();
    } finally {
      setSavingNoteId("");
    }
  }

  async function deleteSelectedNotes() {
    if (selectedNoteIds.length === 0) return;
    setBatchDeleting(true);
    try {
      for (const noteId of selectedNoteIds) {
        await apiFetch(`/notes/${noteId}`, { method: "DELETE" });
      }
      setSelectedNoteIds([]);
      await load();
    } finally {
      setBatchDeleting(false);
    }
  }

  async function exportMarkdown() {
    if (!docId) return;
    const blob = await loadAuthorizedBlob(`/notes/export/${docId}`);
    downloadBlob(blob, `learnai-notes-${docId}.md`);
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">筆記</h1>
          <p className="mt-1 text-sm text-zinc-500">
            管理從對話、測驗與閃卡保存下來的文字
          </p>
        </div>
        {docId ? (
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
            onClick={exportMarkdown}
          >
            <Download size={16} />
            匯出 Markdown
          </button>
        ) : (
          <button
            className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-400"
            disabled
          >
            <Download size={16} />
            匯出 Markdown
          </button>
        )}
      </div>
      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <aside className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="space-y-3">
            <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-zinc-900">
              <Filter size={16} />
              篩選保存內容
            </div>
            <select
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              value={courseId}
              onChange={(event) => {
                setCourseId(event.target.value);
                setDocId("");
              }}
            >
              <option value="">個人文件</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.title}
                </option>
              ))}
            </select>
            <select
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              value={docId}
              onChange={(event) => setDocId(event.target.value)}
            >
              <option value="">全部文件</option>
              {scopeDocuments.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                  {courseId || ("user_id" in doc && doc.user_id !== user?.id)
                    ? "（課程共享）"
                    : ""}
                </option>
              ))}
            </select>
            <input
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              value={q}
              onChange={(event) => setQ(event.target.value)}
              placeholder="搜尋筆記"
            />
            <div className="rounded-lg border border-dashed border-zinc-200 bg-zinc-50 px-3 py-3 text-sm leading-6 text-zinc-600">
              在對話、測驗解析或閃卡頁按「存到筆記」後，內容會出現在這裡。
              你可以再編輯、刪除、批量整理或依文件匯出 Markdown。
            </div>
          </div>
        </aside>
        <section className="space-y-3">
          {notes.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm shadow-sm">
              <button
                type="button"
                className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                onClick={() =>
                  setSelectedNoteIds(visibleNotes.map((note) => note.id))
                }
              >
                全選筆記
              </button>
              <button
                type="button"
                className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:text-zinc-400"
                onClick={() => setSelectedNoteIds([])}
                disabled={selectedNoteIds.length === 0}
              >
                清空
              </button>
              <span className="text-xs text-zinc-500">
                已選 {selectedNoteIds.length} / {visibleNotes.length}
              </span>
              <LoadingButton
                className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                onClick={deleteSelectedNotes}
                disabled={selectedNoteIds.length === 0}
                loading={batchDeleting}
                loadingText="刪除中"
              >
                批量刪除
              </LoadingButton>
            </div>
          )}
          {visibleNotes.map((note) => (
            <article
              key={note.id}
              className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm"
            >
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm text-zinc-500">
                  <input
                    type="checkbox"
                    checked={selectedNoteIds.includes(note.id)}
                    onChange={(event) =>
                      setSelectedNoteIds((current) =>
                        event.target.checked
                          ? [...current, note.id]
                          : current.filter((id) => id !== note.id),
                      )
                    }
                    aria-label="選取筆記"
                  />
                  <NotebookPen size={16} />
                  {sourceTypeLabel(note.source_type)}{" "}
                  {note.source_page ? `· 第 ${note.source_page} 頁` : ""}
                </div>
                <div className="flex items-center gap-2">
                  {editingNoteId === note.id ? (
                    <button
                      type="button"
                      className="text-xs text-zinc-600 hover:text-zinc-900"
                      onClick={cancelEditing}
                    >
                      取消
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-900"
                      onClick={() => startEditing(note)}
                    >
                      <Pencil size={13} />
                      編輯
                    </button>
                  )}
                  <button
                    className="text-xs text-red-600"
                    onClick={() => deleteNote(note.id)}
                  >
                    刪除
                  </button>
                </div>
              </div>
              {editingNoteId === note.id ? (
                <div className="space-y-2">
                  <textarea
                    className="min-h-40 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                    value={editingContent}
                    onChange={(event) => setEditingContent(event.target.value)}
                  />
                  <LoadingButton
                    className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:bg-zinc-300"
                    onClick={() => saveNote(note)}
                    loading={savingNoteId === note.id}
                    loadingText="儲存中"
                    disabled={!editingContent.trim()}
                    icon={<CheckCircle2 size={16} />}
                  >
                    儲存
                  </LoadingButton>
                </div>
              ) : (
                <MarkdownContent className="text-sm">
                  {note.content}
                </MarkdownContent>
              )}
            </article>
          ))}
          {visibleNotes.length === 0 && (
            <div className="rounded-lg border border-zinc-200 bg-white p-8 text-sm text-zinc-500">
              尚無筆記
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

async function loadAuthorizedBlob(path: string): Promise<Blob> {
  let res = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() });
  if (res.status === 401 && (await refreshToken())) {
    res = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() });
  }
  if (!res.ok) throw new Error("Failed to load file");
  return res.blob();
}

function authHeaders() {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : undefined;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function sourceTypeLabel(sourceType?: string | null) {
  if (sourceType === "chat") return "對話保存";
  if (sourceType === "summary") return "摘要保存";
  if (sourceType === "quiz") return "測驗保存";
  if (sourceType === "flashcard") return "閃卡保存";
  return "保存內容";
}

function queryString(params: Record<string, string>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) search.set(key, value);
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}
