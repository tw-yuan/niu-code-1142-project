import { FormEvent, useEffect, useState } from "react"
import { BookOpen, Copy, Plus, Users } from "lucide-react"
import { ApiError, apiFetch, CourseItem, DocumentItem } from "../lib/api"
import { useAuthStore } from "../store/auth"

export function CoursesPage() {
  type CourseMember = { user_id: string; username: string; email: string | null; role: string; joined_at: string }
  type CourseProgress = { user_id: string; username: string; email: string | null; role: string; chat_sessions: number; chat_messages: number; notes: number; flashcards: number; quizzes: number; last_activity_at: string | null }
  const [courses, setCourses] = useState<CourseItem[]>([])
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [selected, setSelected] = useState<CourseItem | null>(null)
  const [title, setTitle] = useState("")
  const [courseTitle, setCourseTitle] = useState("")
  const [courseDescription, setCourseDescription] = useState("")
  const [joinCode, setJoinCode] = useState("")
  const [docId, setDocId] = useState("")
  const [members, setMembers] = useState<CourseMember[]>([])
  const [progress, setProgress] = useState<CourseProgress[]>([])
  const [progressError, setProgressError] = useState("")
  const user = useAuthStore((state) => state.user)
  const canManage = selected?.role === "instructor"
  const isOwner = Boolean(selected && selected.owner_id === user?.id)

  async function load() {
    const [nextCourses, docs] = await Promise.all([
      apiFetch<CourseItem[]>("/courses"),
      apiFetch<DocumentItem[]>("/documents"),
    ])
    setCourses(nextCourses)
    setDocuments(docs.filter((doc) => doc.status === "ready"))
    if (!selected && nextCourses[0]) await openCourse(nextCourses[0].id)
  }

  async function openCourse(id: string) {
    const course = await apiFetch<CourseItem>(`/courses/${id}`)
    const nextMembers = await apiFetch<CourseMember[]>(`/courses/${id}/members`)
    setProgressError("")
    const nextProgress = await apiFetch<{ students: CourseProgress[] }>(`/courses/${id}/progress`).catch((err) => {
      if (err instanceof ApiError && err.status === 403) {
        setProgressError("僅教師可查看")
      } else {
        setProgressError("進度載入失敗")
      }
      return { students: [] }
    })
    setSelected(course)
    setCourseTitle(course.title)
    setCourseDescription(course.description ?? "")
    setMembers(nextMembers)
    setProgress(nextProgress.students)
  }

  useEffect(() => {
    load().catch(() => undefined)
  }, [])

  async function create(event: FormEvent) {
    event.preventDefault()
    if (!title.trim()) return
    const course = await apiFetch<CourseItem>("/courses", {
      method: "POST",
      body: JSON.stringify({ title }),
    })
    setTitle("")
    await load()
    await openCourse(course.id)
  }

  async function join(event: FormEvent) {
    event.preventDefault()
    if (!joinCode.trim()) return
    const course = await apiFetch<CourseItem>("/courses/join", {
      method: "POST",
      body: JSON.stringify({ join_code: joinCode.trim().toUpperCase() }),
    })
    setJoinCode("")
    await load()
    await openCourse(course.id)
  }

  async function addDocument() {
    if (!selected || !docId) return
    await apiFetch(`/courses/${selected.id}/documents`, {
      method: "POST",
      body: JSON.stringify({ doc_id: docId }),
    })
    await openCourse(selected.id)
  }

  async function saveCourse() {
    if (!selected || !canManage || !courseTitle.trim()) return
    const updated = await apiFetch<CourseItem>(`/courses/${selected.id}`, {
      method: "PUT",
      body: JSON.stringify({
        title: courseTitle.trim(),
        description: courseDescription.trim() || null,
      }),
    })
    await load()
    await openCourse(updated.id)
  }

  async function resetJoinCode() {
    if (!selected || !isOwner) return
    const updated = await apiFetch<CourseItem>(`/courses/${selected.id}/join-code/reset`, { method: "POST" })
    await load()
    await openCourse(updated.id)
  }

  async function updateMemberRole(member: CourseMember, role: "student" | "instructor") {
    if (!selected || !canManage || member.role === role) return
    await apiFetch(`/courses/${selected.id}/members/${member.user_id}`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    })
    await openCourse(selected.id)
  }

  async function removeMember(member: CourseMember) {
    if (!selected || !canManage) return
    if (!window.confirm(`確定移除 ${member.username ?? member.user_id}？`)) return
    await apiFetch(`/courses/${selected.id}/members/${member.user_id}`, { method: "DELETE" })
    await openCourse(selected.id)
  }

  async function removeDocument(id: string) {
    if (!selected) return
    await apiFetch(`/courses/${selected.id}/documents/${id}`, { method: "DELETE" })
    await openCourse(selected.id)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">課程</h1>
        <p className="mt-1 text-sm text-zinc-500">共用教材與課程 RAG 範圍</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <aside className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <form className="mb-5 space-y-3" onSubmit={create}>
            <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="課程名稱" />
            <button className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">
              <Plus size={16} />
              建立課程
            </button>
          </form>
          <form className="mb-5 flex gap-2" onSubmit={join}>
            <input className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={joinCode} onChange={(event) => setJoinCode(event.target.value)} placeholder="邀請碼" />
            <button className="rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50">加入</button>
          </form>
          <div className="space-y-2">
            {courses.map((course) => (
              <button key={course.id} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-zinc-50" onClick={() => openCourse(course.id)}>
                <BookOpen size={16} className="text-zinc-500" />
                {course.title}
              </button>
            ))}
          </div>
        </aside>
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          {selected ? (
            <div>
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  {canManage ? (
                    <div className="grid max-w-xl gap-2">
                      <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm font-semibold" value={courseTitle} onChange={(event) => setCourseTitle(event.target.value)} />
                      <textarea className="min-h-20 rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={courseDescription} onChange={(event) => setCourseDescription(event.target.value)} placeholder="課程描述" />
                      <button className="w-fit rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700" onClick={saveCourse}>儲存</button>
                    </div>
                  ) : (
                    <>
                      <h2 className="text-lg font-semibold">{selected.title}</h2>
                      <p className="mt-1 text-sm text-zinc-500">{selected.description}</p>
                    </>
                  )}
                  {selected.join_code && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="inline-flex items-center gap-2 rounded-md bg-zinc-100 px-2 py-1 text-xs text-zinc-700" onClick={() => navigator.clipboard.writeText(selected.join_code ?? "")}>
                        <Copy size={14} />
                        {selected.join_code}
                      </button>
                      {isOwner && (
                        <button className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50" onClick={resetJoinCode}>
                          重置
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 text-sm text-zinc-500">
                  <Users size={16} />
                  {members.length} 位成員
                </div>
              </div>
              <div className="mb-5 grid gap-3 lg:grid-cols-2">
                <section className="rounded-lg border border-zinc-200">
                  <div className="border-b border-zinc-200 px-3 py-2 text-sm font-medium">成員</div>
                  <div className="max-h-64 overflow-y-auto divide-y divide-zinc-100">
                    {members.map((member) => (
                      <div key={member.user_id} className="px-3 py-2 text-sm">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate font-medium">{member.username ?? member.user_id}</div>
                            <div className="truncate text-xs text-zinc-500">{member.email ?? ""} · {member.role}</div>
                          </div>
                          {canManage && member.user_id !== selected.owner_id && (
                            <div className="flex shrink-0 items-center gap-2">
                              <select className="rounded-md border border-zinc-200 px-2 py-1 text-xs" value={member.role} onChange={(event) => updateMemberRole(member, event.target.value as "student" | "instructor")}>
                                <option value="student">student</option>
                                <option value="instructor">instructor</option>
                              </select>
                              <button className="text-xs text-red-600" onClick={() => removeMember(member)}>移除</button>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
                <section className="rounded-lg border border-zinc-200">
                  <div className="border-b border-zinc-200 px-3 py-2 text-sm font-medium">學生進度</div>
                  <div className="max-h-64 overflow-y-auto divide-y divide-zinc-100">
                    {progress.map((item) => (
                      <div key={item.user_id} className="grid grid-cols-[1fr_auto] gap-3 px-3 py-2 text-sm">
                        <div>
                          <div className="font-medium">{item.username}</div>
                          <div className="text-xs text-zinc-500">
                            對話 {item.chat_sessions} / 訊息 {item.chat_messages} / 筆記 {item.notes}
                          </div>
                        </div>
                        <div className="text-right text-xs text-zinc-500">
                          測驗 {item.quizzes}
                          <br />
                          閃卡 {item.flashcards}
                        </div>
                      </div>
                    ))}
                    {progress.length === 0 && <div className="px-3 py-8 text-sm text-zinc-500">{progressError || "目前沒有可顯示的進度"}</div>}
                  </div>
                </section>
              </div>
              {canManage && (
                <div className="mb-5 flex gap-2">
                  <select className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={docId} onChange={(event) => setDocId(event.target.value)}>
                    <option value="">選擇我的文件</option>
                    {documents.map((doc) => (
                      <option key={doc.id} value={doc.id}>{doc.filename}</option>
                    ))}
                  </select>
                  <button className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700" onClick={addDocument}>加入</button>
                </div>
              )}
              <div className="divide-y divide-zinc-100">
                {(selected.documents ?? []).map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between py-3 text-sm">
                    <div>
                      <div className="font-medium">{doc.filename}</div>
                      <div className="text-xs text-zinc-500">{doc.status}</div>
                    </div>
                    {canManage && (
                      <button className="text-xs text-red-600" onClick={() => removeDocument(doc.id)}>移除</button>
                    )}
                  </div>
                ))}
                {(selected.documents ?? []).length === 0 && <div className="py-8 text-sm text-zinc-500">尚無課程文件</div>}
              </div>
            </div>
          ) : (
            <div className="text-sm text-zinc-500">選擇或建立課程</div>
          )}
        </section>
      </div>
    </div>
  )
}
