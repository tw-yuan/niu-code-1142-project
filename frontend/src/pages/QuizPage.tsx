import { FormEvent, useEffect, useMemo, useState } from "react"
import { CheckCircle2, ListChecks, Plus, Wand2 } from "lucide-react"
import { Link, useLocation, useParams } from "react-router-dom"
import { AIGeneratedBadge } from "../components/app/AIGeneratedBadge"
import { apiFetch, CourseItem, DocumentItem, QuizDiagnostic, QuizItem } from "../lib/api"
import { streamFetch } from "../lib/stream"
import { useAuthStore } from "../store/auth"

export function QuizPage() {
  const { id } = useParams()
  const user = useAuthStore((state) => state.user)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [quizzes, setQuizzes] = useState<QuizItem[]>([])
  const [docId, setDocId] = useState("")
  const [courseId, setCourseId] = useState("")
  const [courses, setCourses] = useState<CourseItem[]>([])
  const [publishToCourse, setPublishToCourse] = useState(false)
  const [quizTitle, setQuizTitle] = useState("")
  const [difficulty, setDifficulty] = useState("medium")
  const [count, setCount] = useState(5)
  const [preview, setPreview] = useState("")
  const [error, setError] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [score, setScore] = useState<number | null>(null)
  const [diagnostics, setDiagnostics] = useState<QuizDiagnostic[]>([])
  const [wrongbook, setWrongbook] = useState<Array<Record<string, unknown>>>([])
  const [wrongbookMessage, setWrongbookMessage] = useState("")
  const location = useLocation()
  const isWrongbook = location.pathname.endsWith("/wrongbook")

  const activeQuiz = useMemo(() => quizzes.find((quiz) => quiz.id === id), [id, quizzes])

  async function load() {
    const [docs, nextQuizzes, wrongbookRows, nextCourses] = await Promise.all([
      apiFetch<DocumentItem[]>("/documents"),
      apiFetch<QuizItem[]>("/quiz"),
      isWrongbook ? apiFetch<Array<Record<string, unknown>>>("/quiz/wrongbook") : Promise.resolve([]),
      apiFetch<CourseItem[]>("/courses").catch(() => []),
    ])
    const ready = docs.filter((doc) => doc.status === "ready")
    setDocuments(ready)
    setQuizzes(nextQuizzes)
    setWrongbook(wrongbookRows)
    setCourses(nextCourses)
    if (!docId && ready[0]) setDocId(ready[0].id)
  }

  useEffect(() => {
    load().catch(() => undefined)
  }, [isWrongbook])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const doc = params.get("doc")
    const course = params.get("course")
    if (doc) setDocId(doc)
    if (course) {
      setCourseId(course)
      setPublishToCourse(true)
    }
  }, [location.search])

  useEffect(() => {
    setAnswers({})
    setScore(null)
    setDiagnostics([])
  }, [id])

  async function generate() {
    if (!docId || user?.quota_status === "exceeded") return
    setPreview("")
    setError("")
    setStreaming(true)
    let next = ""
    let failed = false
    try {
      for await (const event of streamFetch("/quiz/stream", {
        doc_ids: [docId],
        types: ["MC"],
        count,
        difficulty,
        title: quizTitle.trim() || undefined,
        course_id: courseId || undefined,
        publish_to_course: publishToCourse && Boolean(courseId),
      })) {
        if (event.type === "chunk") {
          next += event.content
          setPreview(next)
        } else if (event.type === "error") {
          failed = true
          setError(event.message)
        }
      }
      if (!failed) await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "測驗生成失敗")
    } finally {
      setStreaming(false)
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!activeQuiz) return
    const result = await apiFetch<{ total_score: number; diagnostics: QuizDiagnostic[] }>(`/quiz/${activeQuiz.id}/attempt`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    })
    setScore(result.total_score)
    setDiagnostics(result.diagnostics ?? [])
  }

  async function createWrongbookFlashcards() {
    setWrongbookMessage("")
    const created = await apiFetch<Array<Record<string, unknown>>>("/flashcards/from-wrongbook", {
      method: "POST",
      body: JSON.stringify({ limit: 20 }),
    })
    setWrongbookMessage(`已建立 ${created.length} 張錯題閃卡`)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">測驗</h1>
        <p className="mt-1 text-sm text-zinc-500">生成、作答與複習</p>
      </div>
      <AIGeneratedBadge />
      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <aside className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-semibold">生成測驗</h2>
          <input className="mb-3 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={quizTitle} onChange={(event) => setQuizTitle(event.target.value)} placeholder="測驗標題（選填）" />
          <select className="mb-3 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={docId} onChange={(event) => setDocId(event.target.value)}>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename}{doc.user_id !== user?.id ? "（課程共享）" : ""}
              </option>
            ))}
          </select>
          <div className="mb-3 grid grid-cols-2 gap-2">
            <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" type="number" min={1} max={50} value={count} onChange={(event) => setCount(Number(event.target.value))} />
            <select className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
              <option value="easy">簡單</option>
              <option value="medium">中等</option>
              <option value="hard">困難</option>
            </select>
          </div>
          <label className="mb-3 flex items-center gap-2 text-sm text-zinc-700">
            <input type="checkbox" checked={publishToCourse} onChange={(event) => setPublishToCourse(event.target.checked)} />
            發布到課程
          </label>
          {publishToCourse && (
            <select className="mb-3 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm" value={courseId} onChange={(event) => setCourseId(event.target.value)}>
              <option value="">選擇課程</option>
              {courses.filter((course) => course.role === "instructor").map((course) => (
                <option key={course.id} value={course.id}>{course.title}</option>
              ))}
            </select>
          )}
          <button className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300" onClick={generate} disabled={!docId || streaming || user?.quota_status === "exceeded"}>
            <Wand2 size={16} />
            {streaming ? "生成中" : "生成測驗"}
          </button>
          {error && <div className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
          {preview && <pre className="mt-4 max-h-64 overflow-auto rounded-md bg-zinc-50 p-3 text-xs">{preview}</pre>}
          <h2 className="mb-3 mt-6 font-semibold">測驗列表</h2>
          <div className="space-y-2">
            {quizzes.map((quiz) => (
              <Link key={quiz.id} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-zinc-50" to={`/quiz/${quiz.id}`}>
                <ListChecks size={16} className="text-zinc-500" />
                {quiz.title}
              </Link>
            ))}
          </div>
        </aside>
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          {isWrongbook ? (
            <div className="space-y-3">
              <h2 className="font-semibold">錯題本</h2>
              <div className="flex flex-wrap items-center gap-2">
                <button className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700" onClick={createWrongbookFlashcards}>
                  <Plus size={16} />
                  錯題轉閃卡
                </button>
                {wrongbookMessage && <span className="text-sm text-emerald-700">{wrongbookMessage}</span>}
              </div>
              {wrongbook.map((item, index) => (
                <article key={index} className="rounded-lg border border-zinc-200 p-4 text-sm">
                  <div className="font-medium">{String(item.question ?? "")}</div>
                  {item.submitted_answer !== undefined && item.submitted_answer !== null && (
                    <div className="mt-2 text-red-600">你的答案：{String(item.submitted_answer)}</div>
                  )}
                  <div className="mt-2 text-zinc-600">答案：{String(item.answer ?? "")}</div>
                  {item.explanation !== undefined && item.explanation !== null && (
                    <div className="mt-1 text-zinc-500">{String(item.explanation)}</div>
                  )}
                  {item.source_page !== undefined && item.source_page !== null && (
                    <div className="mt-2 text-xs text-zinc-400">來源頁：{String(item.source_page)}</div>
                  )}
                </article>
              ))}
              {wrongbook.length === 0 && <div className="text-sm text-zinc-500">尚無錯題紀錄</div>}
            </div>
          ) : activeQuiz ? (
            <form onSubmit={submit} className="space-y-5">
              <h2 className="font-semibold">{activeQuiz.title}</h2>
              {activeQuiz.questions.map((question, index) => (
                <div key={index} className="rounded-lg border border-zinc-200 p-4">
                  <div className="mb-3 text-sm font-medium">{index + 1}. {String(question.question ?? question.prompt ?? "")}</div>
                  <div className="space-y-2">
                    {optionsFor(question).map((option) => (
                      <label key={option} className="flex items-center gap-2 text-sm">
                        <input type="radio" name={`q-${index}`} value={option} checked={answers[String(index)] === option} onChange={(event) => setAnswers((prev) => ({ ...prev, [String(index)]: event.target.value }))} />
                        {option}
                      </label>
                    ))}
                  </div>
                  {score !== null && <QuestionDiagnostic diagnostic={diagnostics.find((item) => item.question_index === index)} question={question} />}
                </div>
              ))}
              <button className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                <CheckCircle2 size={16} />
                提交
              </button>
              {score !== null && <span className="ml-3 text-sm font-medium text-indigo-700">分數：{Math.round(score * 100)}%</span>}
            </form>
          ) : (
            <div className="text-sm text-zinc-500">選擇或生成一份測驗</div>
          )}
        </section>
      </div>
    </div>
  )
}

function optionsFor(question: Record<string, unknown>) {
  const options = question.options
  if (Array.isArray(options)) return options.map(String)
  return ["A", "B", "C", "D"].filter((key) => question[key]).map((key) => String(question[key]))
}

function QuestionDiagnostic({
  diagnostic,
  question,
}: {
  diagnostic?: QuizDiagnostic
  question: Record<string, unknown>
}) {
  const isCorrect = diagnostic?.is_correct
  const explanation = diagnostic?.explanation ?? question.explanation
  return (
    <div className={["mt-3 rounded-md px-3 py-2 text-xs", isCorrect ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"].join(" ")}>
      <div className="font-medium">{isCorrect ? "答對" : "需複習"}</div>
      <div className="mt-1">答案：{String(diagnostic?.answer ?? question.answer ?? "")}</div>
      {diagnostic?.submitted_answer !== undefined && (
        <div className="mt-1">你的答案：{String(diagnostic.submitted_answer ?? "未作答")}</div>
      )}
      {explanation !== undefined && explanation !== null && (
        <div className="mt-1 leading-5">{String(explanation)}</div>
      )}
    </div>
  )
}
