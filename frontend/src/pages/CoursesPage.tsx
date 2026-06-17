import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  BrainCircuit,
  CalendarClock,
  CheckCircle2,
  Copy,
  FileText,
  Megaphone,
  MessageCircleQuestion,
  ListChecks,
  LogOut,
  MessageSquareText,
  Network,
  NotebookPen,
  Plus,
  Trash2,
  Users,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { LoadingButton } from "../components/app/LoadingButton";
import {
  ApiError,
  apiBlob,
  apiFetch,
  CourseAnnouncementItem,
  CourseAssignmentItem,
  CourseHelpRequestItem,
  CourseItem,
  CourseProgress,
  CourseProgressStudent,
  CourseQuestionBankItem,
  DocumentItem,
  QuizItem,
} from "../lib/api";
import { useAuthStore } from "../store/auth";

type CourseTab =
  | "overview"
  | "materials"
  | "tasks"
  | "interaction"
  | "people"
  | "question-bank";

export function CoursesPage() {
  type CourseMember = {
    user_id: string;
    username: string;
    email: string | null;
    role: string;
    joined_at: string;
  };
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<CourseItem | null>(null);
  const [title, setTitle] = useState("");
  const [courseTitle, setCourseTitle] = useState("");
  const [courseDescription, setCourseDescription] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [addDocumentIds, setAddDocumentIds] = useState<string[]>([]);
  const [members, setMembers] = useState<CourseMember[]>([]);
  const [progress, setProgress] = useState<CourseProgressStudent[]>([]);
  const [quizSummary, setQuizSummary] = useState<
    CourseProgress["quiz_summary"]
  >([]);
  const [courseQuizzes, setCourseQuizzes] = useState<QuizItem[]>([]);
  const [questionBank, setQuestionBank] = useState<CourseQuestionBankItem[]>(
    [],
  );
  const [assignments, setAssignments] = useState<CourseAssignmentItem[]>([]);
  const [announcements, setAnnouncements] = useState<CourseAnnouncementItem[]>(
    [],
  );
  const [helpRequests, setHelpRequests] = useState<CourseHelpRequestItem[]>([]);
  const [assignmentTitle, setAssignmentTitle] = useState("");
  const [assignmentDescription, setAssignmentDescription] = useState("");
  const [assignmentKind, setAssignmentKind] =
    useState<CourseAssignmentItem["kind"]>("custom");
  const [assignmentDocId, setAssignmentDocId] = useState("");
  const [assignmentQuizId, setAssignmentQuizId] = useState("");
  const [assignmentDueAt, setAssignmentDueAt] = useState("");
  const [announcementTitle, setAnnouncementTitle] = useState("");
  const [announcementContent, setAnnouncementContent] = useState("");
  const [helpTitle, setHelpTitle] = useState("");
  const [helpContent, setHelpContent] = useState("");
  const [helpPriority, setHelpPriority] = useState<"low" | "normal" | "high">(
    "normal",
  );
  const [activeTab, setActiveTab] = useState<CourseTab>("overview");
  const [selectedMaterialIds, setSelectedMaterialIds] = useState<string[]>([]);
  const [progressError, setProgressError] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const location = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const canCreateCourse = user?.role === "teacher" || user?.role === "admin";
  const canManage = selected?.role === "instructor" || selected?.role === "ta";
  const canEditCourse = selected?.role === "instructor";
  const canManageMemberRoles = selected?.role === "instructor";
  const isOwner = Boolean(selected && selected.owner_id === user?.id);
  const upcomingDeadlines = useMemo(
    () => buildUpcomingDeadlines(assignments, courseQuizzes),
    [assignments, courseQuizzes],
  );
  const courseDocuments = useMemo(
    () =>
      (selected?.documents ?? []).filter(
        (doc) => doc.course_status !== "removed",
      ),
    [selected],
  );
  const readyCourseDocuments = useMemo(
    () => courseDocuments.filter((doc) => doc.status === "ready"),
    [courseDocuments],
  );
  const addableDocuments = useMemo(() => {
    const activeCourseDocIds = new Set(courseDocuments.map((doc) => doc.id));
    return documents.filter((doc) => !activeCourseDocIds.has(doc.id));
  }, [courseDocuments, documents]);
  const allAddableDocumentsSelected =
    addableDocuments.length > 0 &&
    addableDocuments.every((doc) => addDocumentIds.includes(doc.id));
  const selectedReadyMaterialIds = selectedMaterialIds.filter((docId) =>
    readyCourseDocuments.some((doc) => doc.id === docId),
  );
  const materialActionDocIds =
    selectedReadyMaterialIds.length > 0
      ? selectedReadyMaterialIds
      : readyCourseDocuments.map((doc) => doc.id);
  const unreadAnnouncements = announcements.filter(
    (announcement) => !announcement.read_at,
  ).length;
  const openHelpRequests = helpRequests.filter(
    (request) => request.status !== "resolved",
  ).length;
  const pendingAssignments = assignments.filter(
    (assignment) =>
      !["completed", "late"].includes(assignment.completion.status),
  ).length;
  const approvedQuestions = questionBank.filter(
    (item) => item.status === "approved",
  ).length;
  const courseTabs = [
    { id: "overview" as CourseTab, label: "概覽", icon: CalendarClock },
    {
      id: "materials" as CourseTab,
      label: "教材",
      icon: FileText,
      count: courseDocuments.length,
    },
    {
      id: "tasks" as CourseTab,
      label: "任務",
      icon: ListChecks,
      count: assignments.length + courseQuizzes.length,
    },
    {
      id: "interaction" as CourseTab,
      label: "公告/求助",
      icon: Megaphone,
      count: unreadAnnouncements + openHelpRequests,
    },
    {
      id: "people" as CourseTab,
      label: "成員/進度",
      icon: Users,
      count: members.length,
    },
    ...(canManage
      ? [
          {
            id: "question-bank" as CourseTab,
            label: "題庫",
            icon: ListChecks,
            count: questionBank.length,
          },
        ]
      : []),
  ];

  useEffect(() => {
    if (activeTab === "question-bank" && !canManage) {
      setCourseTab("overview");
    }
  }, [activeTab, canManage]);

  async function load() {
    const [nextCourses, docs] = await Promise.all([
      apiFetch<CourseItem[]>("/courses"),
      apiFetch<DocumentItem[]>("/documents"),
    ]);
    setCourses(nextCourses);
    setDocuments(
      docs.filter((doc) => doc.status === "ready" && doc.user_id === user?.id),
    );
    const params = new URLSearchParams(location.search);
    const requestedCourseId = params.get("course");
    const requestedTab = parseCourseTab(params.get("tab")) ?? "overview";
    const targetCourseId =
      requestedCourseId || (!selected ? nextCourses[0]?.id : null);
    if (targetCourseId) await openCourse(targetCourseId, requestedTab, false);
  }

  async function openCourse(
    id: string,
    nextTab: CourseTab = "overview",
    syncUrl = true,
  ) {
    const course = await apiFetch<CourseItem>(`/courses/${id}`);
    const [
      nextMembers,
      nextCourseQuizzes,
      nextQuestionBank,
      nextAssignments,
      nextAnnouncements,
      nextHelpRequests,
    ] = await Promise.all([
      apiFetch<CourseMember[]>(`/courses/${id}/members`),
      apiFetch<QuizItem[]>(`/courses/${id}/quizzes`),
      apiFetch<CourseQuestionBankItem[]>(`/courses/${id}/question-bank`).catch(
        (err) => {
          if (err instanceof ApiError && err.status === 403) return [];
          throw err;
        },
      ),
      apiFetch<CourseAssignmentItem[]>(`/courses/${id}/assignments`),
      apiFetch<CourseAnnouncementItem[]>(`/courses/${id}/announcements`),
      apiFetch<CourseHelpRequestItem[]>(`/courses/${id}/help-requests`),
    ]);
    setProgressError("");
    const nextProgress = await apiFetch<CourseProgress>(
      `/courses/${id}/progress`,
    ).catch((err) => {
      if (err instanceof ApiError && err.status === 403) {
        setProgressError("僅教師可查看");
      } else {
        setProgressError("進度載入失敗");
      }
      return {
        course_id: id,
        document_count: 0,
        published_quizzes: 0,
        students: [],
        quiz_summary: [],
      };
    });
    setSelected(course);
    setCourseTitle(course.title);
    setCourseDescription(course.description ?? "");
    setMembers(nextMembers);
    setCourseQuizzes(nextCourseQuizzes);
    setQuestionBank(nextQuestionBank);
    setAssignments(nextAssignments);
    setAnnouncements(nextAnnouncements);
    setHelpRequests(nextHelpRequests);
    setProgress(nextProgress.students);
    setQuizSummary(nextProgress.quiz_summary);
    setSelectedMaterialIds([]);
    setAddDocumentIds([]);
    const visibleTab = normalizeCourseTab(nextTab, course);
    setActiveTab(visibleTab);
    if (syncUrl) navigate(coursePath(id, visibleTab));
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const requestedCourseId = params.get("course");
    const requestedTab = parseCourseTab(params.get("tab"));
    if (requestedCourseId && requestedCourseId !== selected?.id) {
      openCourse(requestedCourseId, requestedTab ?? "overview", false).catch(
        () => undefined,
      );
      return;
    }
    if (requestedTab && selected) {
      setActiveTab(normalizeCourseTab(requestedTab, selected));
    }
  }, [location.search, selected?.id]);

  function setCourseTab(tab: CourseTab) {
    const nextTab = selected ? normalizeCourseTab(tab, selected) : tab;
    setActiveTab(nextTab);
    if (selected) navigate(coursePath(selected.id, nextTab), { replace: true });
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) return;
    setBusyAction("create");
    try {
      const course = await apiFetch<CourseItem>("/courses", {
        method: "POST",
        body: JSON.stringify({ title }),
      });
      setTitle("");
      await load();
      await openCourse(course.id);
    } finally {
      setBusyAction("");
    }
  }

  async function join(event: FormEvent) {
    event.preventDefault();
    if (!joinCode.trim()) return;
    setBusyAction("join");
    try {
      const course = await apiFetch<CourseItem>("/courses/join", {
        method: "POST",
        body: JSON.stringify({ join_code: joinCode.trim().toUpperCase() }),
      });
      setJoinCode("");
      await load();
      await openCourse(course.id);
    } finally {
      setBusyAction("");
    }
  }

  async function addDocument() {
    if (!selected || addDocumentIds.length === 0) return;
    setBusyAction("add-document");
    try {
      await apiFetch(`/courses/${selected.id}/documents`, {
        method: "POST",
        body: JSON.stringify({ doc_ids: addDocumentIds }),
      });
      await openCourse(selected.id, "materials");
    } finally {
      setBusyAction("");
    }
  }

  async function saveCourse() {
    if (!selected || !canEditCourse || !courseTitle.trim()) return;
    setBusyAction("save-course");
    try {
      const updated = await apiFetch<CourseItem>(`/courses/${selected.id}`, {
        method: "PUT",
        body: JSON.stringify({
          title: courseTitle.trim(),
          description: courseDescription.trim() || null,
        }),
      });
      await load();
      await openCourse(updated.id);
    } finally {
      setBusyAction("");
    }
  }

  async function resetJoinCode() {
    if (!selected || !isOwner) return;
    setBusyAction("reset-code");
    try {
      const updated = await apiFetch<CourseItem>(
        `/courses/${selected.id}/join-code/reset`,
        { method: "POST" },
      );
      await load();
      await openCourse(updated.id);
    } finally {
      setBusyAction("");
    }
  }

  async function updateMemberRole(
    member: CourseMember,
    role: "student" | "ta" | "instructor",
  ) {
    if (!selected || !canManageMemberRoles || member.role === role) return;
    setBusyAction(`member-role-${member.user_id}`);
    try {
      await apiFetch(`/courses/${selected.id}/members/${member.user_id}`, {
        method: "PUT",
        body: JSON.stringify({ role }),
      });
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function removeMember(member: CourseMember) {
    if (!selected || !canManage) return;
    setBusyAction(`remove-member-${member.user_id}`);
    try {
      await apiFetch(`/courses/${selected.id}/members/${member.user_id}`, {
        method: "DELETE",
      });
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function removeDocument(id: string) {
    if (!selected) return;
    setBusyAction(`remove-document-${id}`);
    try {
      await apiFetch(`/courses/${selected.id}/documents/${id}`, {
        method: "DELETE",
      });
      await openCourse(selected.id, "materials");
    } finally {
      setBusyAction("");
    }
  }

  async function createAssignment(event: FormEvent) {
    event.preventDefault();
    if (!selected || !canManage || !assignmentTitle.trim()) return;
    const needsDoc = assignmentNeedsDocument(assignmentKind);
    if (needsDoc && !assignmentDocId) return;
    if (assignmentKind === "quiz" && !assignmentQuizId) return;
    setBusyAction("create-assignment");
    try {
      await apiFetch<CourseAssignmentItem>(
        `/courses/${selected.id}/assignments`,
        {
          method: "POST",
          body: JSON.stringify({
            title: assignmentTitle.trim(),
            description: assignmentDescription.trim() || null,
            kind: assignmentKind,
            doc_id: needsDoc ? assignmentDocId : null,
            quiz_id: assignmentKind === "quiz" ? assignmentQuizId : null,
            due_at: normalizeDateTimeInput(assignmentDueAt),
            status: "published",
          }),
        },
      );
      setAssignmentTitle("");
      setAssignmentDescription("");
      setAssignmentDueAt("");
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function submitAssignment(assignment: CourseAssignmentItem) {
    if (!selected) return;
    setBusyAction(`submit-assignment-${assignment.id}`);
    try {
      await apiFetch<CourseAssignmentItem>(
        `/courses/${selected.id}/assignments/${assignment.id}/submit`,
        {
          method: "POST",
          body: JSON.stringify({ response: "" }),
        },
      );
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function deleteAssignment(assignment: CourseAssignmentItem) {
    if (!selected || !canManage) return;
    setBusyAction(`delete-assignment-${assignment.id}`);
    try {
      await apiFetch(`/courses/${selected.id}/assignments/${assignment.id}`, {
        method: "DELETE",
      });
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function createAnnouncement(event: FormEvent) {
    event.preventDefault();
    if (
      !selected ||
      !canManage ||
      !announcementTitle.trim() ||
      !announcementContent.trim()
    )
      return;
    setBusyAction("create-announcement");
    try {
      await apiFetch<CourseAnnouncementItem>(
        `/courses/${selected.id}/announcements`,
        {
          method: "POST",
          body: JSON.stringify({
            title: announcementTitle.trim(),
            content: announcementContent.trim(),
            status: "published",
          }),
        },
      );
      setAnnouncementTitle("");
      setAnnouncementContent("");
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function deleteAnnouncement(announcement: CourseAnnouncementItem) {
    if (!selected || !canManage) return;
    setBusyAction(`delete-announcement-${announcement.id}`);
    try {
      await apiFetch(
        `/courses/${selected.id}/announcements/${announcement.id}`,
        { method: "DELETE" },
      );
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function markAnnouncementRead(announcement: CourseAnnouncementItem) {
    if (!selected) return;
    setBusyAction(`read-announcement-${announcement.id}`);
    try {
      await apiFetch(
        `/courses/${selected.id}/announcements/${announcement.id}/read`,
        { method: "POST" },
      );
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function createHelpRequest(event: FormEvent) {
    event.preventDefault();
    if (!selected || !helpTitle.trim()) return;
    setBusyAction("create-help");
    try {
      await apiFetch<CourseHelpRequestItem>(
        `/courses/${selected.id}/help-requests`,
        {
          method: "POST",
          body: JSON.stringify({
            title: helpTitle.trim(),
            content: helpContent.trim() || null,
            priority: helpPriority,
          }),
        },
      );
      setHelpTitle("");
      setHelpContent("");
      setHelpPriority("normal");
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function updateHelpRequest(
    request: CourseHelpRequestItem,
    status: "open" | "in_progress" | "resolved",
  ) {
    if (!selected || !canManage) return;
    setBusyAction(`help-status-${request.id}`);
    try {
      await apiFetch(`/courses/${selected.id}/help-requests/${request.id}`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function updateQuestionReview(
    item: CourseQuestionBankItem,
    status: "draft" | "approved" | "rejected" | "archived",
  ) {
    if (!selected || !canManage) return;
    setBusyAction(`review-question-${item.id}`);
    try {
      await apiFetch(`/courses/${selected.id}/question-bank/${item.id}`, {
        method: "PUT",
        body: JSON.stringify({
          status,
          review_note: item.review_note,
        }),
      });
      await openCourse(selected.id);
    } finally {
      setBusyAction("");
    }
  }

  async function exportProgressCsv() {
    if (!selected || !canManage) return;
    setBusyAction("export-progress");
    try {
      const blob = await apiBlob(`/courses/${selected.id}/progress.csv`);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${safeFilename(selected.title)}-progress.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } finally {
      setBusyAction("");
    }
  }

  async function leaveCourse() {
    if (!selected || isOwner) return;
    setBusyAction("leave");
    try {
      await apiFetch(`/courses/${selected.id}/leave`, { method: "POST" });
      setSelected(null);
      await load();
    } finally {
      setBusyAction("");
    }
  }

  async function deleteCourse() {
    if (!selected || !isOwner) return;
    setBusyAction("delete-course");
    try {
      await apiFetch(`/courses/${selected.id}`, { method: "DELETE" });
      setSelected(null);
      setMembers([]);
      setProgress([]);
      setQuizSummary([]);
      setCourseQuizzes([]);
      setQuestionBank([]);
      setAssignments([]);
      setAnnouncements([]);
      setHelpRequests([]);
      await load();
    } finally {
      setBusyAction("");
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">課程</h1>
        <p className="mt-1 text-sm text-zinc-500">共用教材與課程 RAG 範圍</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="h-fit rounded-lg border border-zinc-200 bg-white p-4 shadow-sm lg:sticky lg:top-5">
          {canCreateCourse ? (
            <form className="mb-5 space-y-3" onSubmit={create}>
              <label
                className="block text-xs font-medium text-zinc-500"
                htmlFor="new-course-title"
              >
                課程名稱
              </label>
              <input
                id="new-course-title"
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
              <LoadingButton
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                loading={busyAction === "create"}
                loadingText="建立中"
                icon={<Plus size={16} />}
              >
                建立課程
              </LoadingButton>
            </form>
          ) : (
            <div className="mb-5 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-3 text-sm text-zinc-600">
              只有教師或管理員可以建立課程。
            </div>
          )}
          <form className="mb-5 flex gap-2" onSubmit={join}>
            <label className="sr-only" htmlFor="course-join-code">
              邀請碼
            </label>
            <input
              id="course-join-code"
              className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              value={joinCode}
              onChange={(event) => setJoinCode(event.target.value)}
              placeholder="邀請碼"
            />
            <LoadingButton
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100"
              loading={busyAction === "join"}
              loadingText="加入中"
            >
              加入
            </LoadingButton>
          </form>
          <div className="max-h-[52vh] space-y-1 overflow-y-auto pr-1 scrollbar-thin">
            {courses.map((course) => (
              <button
                key={course.id}
                className={[
                  "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm",
                  selected?.id === course.id
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-zinc-700 hover:bg-zinc-50",
                ].join(" ")}
                onClick={() => openCourse(course.id)}
              >
                <BookOpen size={16} className="text-zinc-500" />
                <span className="min-w-0 truncate">{course.title}</span>
              </button>
            ))}
          </div>
        </aside>
        <section className="min-w-0 rounded-lg border border-zinc-200 bg-white shadow-sm">
          {selected ? (
            <div className="min-w-0">
              <div className="border-b border-zinc-200 px-5 py-4">
                <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                  <div className="min-w-0 flex-1">
                    {canEditCourse ? (
                      <div className="grid max-w-xl gap-2">
                        <input
                          className="rounded-lg border border-zinc-200 px-3 py-2 text-sm font-semibold"
                          value={courseTitle}
                          onChange={(event) =>
                            setCourseTitle(event.target.value)
                          }
                        />
                        <textarea
                          className="min-h-20 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                          value={courseDescription}
                          onChange={(event) =>
                            setCourseDescription(event.target.value)
                          }
                          placeholder="課程描述"
                        />
                        <LoadingButton
                          className="inline-flex w-fit items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                          onClick={saveCourse}
                          loading={busyAction === "save-course"}
                          loadingText="儲存中"
                        >
                          儲存
                        </LoadingButton>
                      </div>
                    ) : (
                      <>
                        <h2 className="text-lg font-semibold">
                          {selected.title}
                        </h2>
                        <p className="mt-1 text-sm text-zinc-500">
                          {selected.description}
                        </p>
                      </>
                    )}
                    {selected.join_code && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          className="inline-flex items-center gap-2 rounded-md bg-zinc-100 px-2 py-1 text-xs text-zinc-700"
                          onClick={() =>
                            navigator.clipboard.writeText(
                              selected.join_code ?? "",
                            )
                          }
                        >
                          <Copy size={14} />
                          {selected.join_code}
                        </button>
                        {isOwner && (
                          <LoadingButton
                            className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:bg-zinc-100"
                            onClick={resetJoinCode}
                            loading={busyAction === "reset-code"}
                            loadingText="重置中"
                          >
                            重置
                          </LoadingButton>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-600">
                      <Users size={16} />
                      {members.length} 位成員
                    </span>
                    {!isOwner && (
                      <LoadingButton
                        className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:bg-red-50"
                        onClick={leaveCourse}
                        loading={busyAction === "leave"}
                        loadingText="退出中"
                        icon={<LogOut size={16} />}
                      >
                        退出課程
                      </LoadingButton>
                    )}
                    {isOwner && (
                      <LoadingButton
                        className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:bg-red-50"
                        onClick={deleteCourse}
                        loading={busyAction === "delete-course"}
                        loadingText="刪除中"
                        icon={<Trash2 size={16} />}
                      >
                        刪除課程
                      </LoadingButton>
                    )}
                  </div>
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
                  <SummaryMetric
                    label="教材"
                    value={courseDocuments.length}
                    detail={`${courseDocuments.filter((doc) => doc.status === "ready").length} 份可用`}
                  />
                  <SummaryMetric
                    label="任務"
                    value={assignments.length}
                    detail={`${pendingAssignments} 項待完成`}
                  />
                  <SummaryMetric
                    label="測驗"
                    value={courseQuizzes.length}
                    detail={`${courseQuizzes.filter((quiz) => quiz.latest_attempt).length} 項已完成`}
                  />
                  <SummaryMetric
                    label="公告/求助"
                    value={announcements.length + helpRequests.length}
                    detail={`${unreadAnnouncements + openHelpRequests} 項待處理`}
                  />
                  <SummaryMetric
                    label="題庫"
                    value={canManage ? questionBank.length : quizSummary.length}
                    detail={
                      canManage
                        ? `${approvedQuestions} 題已核准`
                        : `${quizSummary.length} 份測驗摘要`
                    }
                  />
                </div>
              </div>
              <div className="overflow-x-auto border-b border-zinc-200 px-4 scrollbar-thin">
                <div className="flex min-w-max gap-1 py-2">
                  {courseTabs.map((tab) => (
                    <button
                      key={tab.id}
                      className={[
                        "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                        activeTab === tab.id
                          ? "bg-indigo-50 text-indigo-700"
                          : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900",
                      ].join(" ")}
                      onClick={() => setCourseTab(tab.id)}
                    >
                      <tab.icon size={15} />
                      {tab.label}
                      {typeof tab.count === "number" && (
                        <span className="rounded bg-white px-1.5 py-0.5 text-xs text-zinc-500">
                          {tab.count}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
              <div
                className={[
                  "mx-5 mb-5 mt-5 grid gap-3 lg:grid-cols-2",
                  activeTab === "overview" || activeTab === "people"
                    ? ""
                    : "hidden",
                ].join(" ")}
              >
                <section
                  className={[
                    "rounded-lg border border-zinc-200 lg:col-span-2",
                    activeTab === "overview" ? "" : "hidden",
                  ].join(" ")}
                >
                  <div className="flex items-center gap-2 border-b border-zinc-200 px-3 py-2 text-sm font-medium">
                    <CalendarClock size={16} className="text-zinc-500" />
                    近期截止
                  </div>
                  <div className="grid gap-2 p-3 md:grid-cols-3">
                    {upcomingDeadlines.map((item) => (
                      <Link
                        key={`${item.kind}-${item.id}`}
                        className="rounded-lg border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50"
                        to={item.href}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate font-medium">
                            {item.title}
                          </span>
                          <span className={deadlineClass(item.due_at)}>
                            {deadlineLabel(item.due_at)}
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-zinc-500">
                          {item.kindLabel} · {formatDateTime(item.due_at)}
                        </div>
                      </Link>
                    ))}
                    {upcomingDeadlines.length === 0 && (
                      <div className="text-sm text-zinc-500 md:col-span-3">
                        目前沒有近期截止項目
                      </div>
                    )}
                  </div>
                </section>
                <section
                  className={[
                    "rounded-lg border border-zinc-200",
                    activeTab === "people" ? "" : "hidden",
                  ].join(" ")}
                >
                  <div className="border-b border-zinc-200 px-3 py-2 text-sm font-medium">
                    成員
                  </div>
                  <div className="max-h-64 overflow-y-auto divide-y divide-zinc-100">
                    {members.map((member) => (
                      <div key={member.user_id} className="px-3 py-2 text-sm">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate font-medium">
                              {member.username ?? member.user_id}
                            </div>
                            <div className="truncate text-xs text-zinc-500">
                              {member.email ?? ""} · {member.role}
                            </div>
                          </div>
                          {canManage &&
                            member.user_id !== selected.owner_id && (
                              <div className="flex shrink-0 items-center gap-2">
                                {canManageMemberRoles && (
                                  <select
                                    className="rounded-md border border-zinc-200 px-2 py-1 text-xs"
                                    value={member.role}
                                    onChange={(event) =>
                                      updateMemberRole(
                                        member,
                                        event.target.value as
                                          | "student"
                                          | "ta"
                                          | "instructor",
                                      )
                                    }
                                  >
                                    <option value="student">student</option>
                                    <option value="ta">ta</option>
                                    <option value="instructor">
                                      instructor
                                    </option>
                                  </select>
                                )}
                                <LoadingButton
                                  className="inline-flex items-center gap-1 text-xs text-red-600 disabled:text-zinc-400"
                                  onClick={() => removeMember(member)}
                                  loading={
                                    busyAction ===
                                    `remove-member-${member.user_id}`
                                  }
                                  loadingText="移除中"
                                >
                                  移除
                                </LoadingButton>
                              </div>
                            )}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
                <section
                  className={[
                    "rounded-lg border border-zinc-200",
                    activeTab === "people" ? "" : "hidden",
                  ].join(" ")}
                >
                  <div className="border-b border-zinc-200 px-3 py-2 text-sm font-medium">
                    <div className="flex items-center justify-between gap-2">
                      <span>學生進度</span>
                      {canManage && (
                        <LoadingButton
                          className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:text-zinc-400"
                          onClick={exportProgressCsv}
                          loading={busyAction === "export-progress"}
                          loadingText="匯出中"
                        >
                          匯出 CSV
                        </LoadingButton>
                      )}
                    </div>
                  </div>
                  <div className="max-h-64 overflow-y-auto divide-y divide-zinc-100">
                    {progress.map((item) => (
                      <div
                        key={item.user_id}
                        className="grid grid-cols-[1fr_auto] gap-3 px-3 py-2 text-sm"
                      >
                        <div>
                          <div className="font-medium">{item.username}</div>
                          <div className="text-xs text-zinc-500">
                            對話 {item.chat_sessions} / 訊息{" "}
                            {item.chat_messages} / 筆記 {item.notes}
                          </div>
                        </div>
                        <div className="text-right text-xs text-zinc-500">
                          <span className={riskClass(item.risk_level)}>
                            {riskLabel(item.risk_level)}
                          </span>
                          <br />
                          測驗 {item.quizzes}/{item.assigned_quizzes} ·{" "}
                          {Math.round(item.quiz_avg_score * 100)}%
                          <br />
                          閃卡 {item.flashcards_mastered}/{item.flashcards}
                        </div>
                      </div>
                    ))}
                    {progress.length === 0 && (
                      <div className="px-3 py-8 text-sm text-zinc-500">
                        {progressError || "目前沒有可顯示的進度"}
                      </div>
                    )}
                  </div>
                </section>
              </div>
              {canManage && activeTab === "materials" && (
                <section className="mx-5 mb-5 mt-5 rounded-lg border border-zinc-200">
                  <div className="flex flex-col gap-3 border-b border-zinc-200 px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Plus size={16} className="text-zinc-500" />
                      加入教材
                      <span className="text-xs font-normal text-zinc-500">
                        已選 {addDocumentIds.length} / {addableDocuments.length}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                        onClick={() =>
                          setAddDocumentIds(
                            addableDocuments.map((doc) => doc.id),
                          )
                        }
                        disabled={addableDocuments.length === 0}
                      >
                        全選文件
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                        onClick={() => setAddDocumentIds([])}
                        disabled={addDocumentIds.length === 0}
                      >
                        清空
                      </button>
                      {allAddableDocumentsSelected && (
                        <span className="text-xs text-indigo-700">已全選</span>
                      )}
                      <LoadingButton
                        className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                        onClick={addDocument}
                        disabled={
                          addDocumentIds.length === 0 ||
                          busyAction === "add-document"
                        }
                        loading={busyAction === "add-document"}
                        loadingText="加入中"
                      >
                        {addDocumentIds.length > 0
                          ? `加入 ${addDocumentIds.length}`
                          : "加入"}
                      </LoadingButton>
                    </div>
                  </div>
                  <div className="max-h-52 overflow-auto px-3 py-2">
                    {addableDocuments.map((doc) => (
                      <label
                        key={doc.id}
                        className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-zinc-50"
                      >
                        <input
                          type="checkbox"
                          checked={addDocumentIds.includes(doc.id)}
                          onChange={(event) => {
                            setAddDocumentIds((current) =>
                              event.target.checked
                                ? [...current, doc.id]
                                : current.filter((item) => item !== doc.id),
                            );
                          }}
                        />
                        <span className="min-w-0 flex-1 truncate">
                          {doc.filename}
                        </span>
                      </label>
                    ))}
                    {addableDocuments.length === 0 && (
                      <div className="px-2 py-3 text-sm text-zinc-500">
                        沒有可加入的 ready 文件
                      </div>
                    )}
                  </div>
                </section>
              )}
              {activeTab === "interaction" && (
                <div className="mx-5 mb-5 mt-5 grid gap-3 xl:grid-cols-2">
                  <section className="rounded-lg border border-zinc-200">
                    <div className="flex items-center gap-2 border-b border-zinc-200 px-3 py-2 text-sm font-medium">
                      <Megaphone size={16} className="text-zinc-500" />
                      課程公告
                    </div>
                    {canManage && (
                      <form
                        className="grid gap-2 border-b border-zinc-200 bg-zinc-50 px-3 py-3"
                        onSubmit={createAnnouncement}
                      >
                        <input
                          className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                          value={announcementTitle}
                          onChange={(event) =>
                            setAnnouncementTitle(event.target.value)
                          }
                          placeholder="公告標題"
                        />
                        <textarea
                          className="min-h-16 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                          value={announcementContent}
                          onChange={(event) =>
                            setAnnouncementContent(event.target.value)
                          }
                          placeholder="公告內容"
                        />
                        <LoadingButton
                          className="inline-flex w-fit items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                          loading={busyAction === "create-announcement"}
                          loadingText="發布中"
                          icon={<Plus size={16} />}
                        >
                          發布
                        </LoadingButton>
                      </form>
                    )}
                    <div className="max-h-80 overflow-y-auto divide-y divide-zinc-100">
                      {announcements.map((announcement) => (
                        <div
                          key={announcement.id}
                          className="px-3 py-3 text-sm"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-medium">
                                  {announcement.title}
                                </span>
                                {!announcement.read_at && (
                                  <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">
                                    未讀
                                  </span>
                                )}
                              </div>
                              <div className="mt-1 whitespace-pre-wrap text-xs leading-5 text-zinc-600">
                                {announcement.content}
                              </div>
                              <div className="mt-2 text-xs text-zinc-500">
                                {formatDateTime(announcement.created_at)}
                                {announcement.created_by_username
                                  ? ` · ${announcement.created_by_username}`
                                  : ""}
                              </div>
                            </div>
                            <div className="flex shrink-0 flex-col gap-2">
                              {!announcement.read_at && !canManage && (
                                <LoadingButton
                                  className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:text-zinc-400"
                                  onClick={() =>
                                    markAnnouncementRead(announcement)
                                  }
                                  loading={
                                    busyAction ===
                                    `read-announcement-${announcement.id}`
                                  }
                                  loadingText="標記中"
                                >
                                  已讀
                                </LoadingButton>
                              )}
                              {canManage && (
                                <LoadingButton
                                  className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:text-zinc-400"
                                  onClick={() =>
                                    deleteAnnouncement(announcement)
                                  }
                                  loading={
                                    busyAction ===
                                    `delete-announcement-${announcement.id}`
                                  }
                                  loadingText="刪除中"
                                  icon={<Trash2 size={13} />}
                                >
                                  刪除
                                </LoadingButton>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                      {announcements.length === 0 && (
                        <div className="px-3 py-8 text-sm text-zinc-500">
                          目前沒有公告
                        </div>
                      )}
                    </div>
                  </section>
                  <section className="rounded-lg border border-zinc-200">
                    <div className="flex items-center gap-2 border-b border-zinc-200 px-3 py-2 text-sm font-medium">
                      <MessageCircleQuestion
                        size={16}
                        className="text-zinc-500"
                      />
                      求助佇列
                    </div>
                    {!canManage && (
                      <form
                        className="grid gap-2 border-b border-zinc-200 bg-zinc-50 px-3 py-3"
                        onSubmit={createHelpRequest}
                      >
                        <input
                          className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                          value={helpTitle}
                          onChange={(event) => setHelpTitle(event.target.value)}
                          placeholder="問題標題"
                        />
                        <textarea
                          className="min-h-16 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                          value={helpContent}
                          onChange={(event) =>
                            setHelpContent(event.target.value)
                          }
                          placeholder="補充說明"
                        />
                        <div className="flex flex-wrap items-center gap-2">
                          <select
                            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                            value={helpPriority}
                            onChange={(event) =>
                              setHelpPriority(
                                event.target.value as "low" | "normal" | "high",
                              )
                            }
                          >
                            <option value="low">低</option>
                            <option value="normal">一般</option>
                            <option value="high">高</option>
                          </select>
                          <LoadingButton
                            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                            loading={busyAction === "create-help"}
                            loadingText="送出中"
                            icon={<Plus size={16} />}
                          >
                            送出
                          </LoadingButton>
                        </div>
                      </form>
                    )}
                    <div className="max-h-80 overflow-y-auto divide-y divide-zinc-100">
                      {helpRequests.map((request) => (
                        <div key={request.id} className="px-3 py-3 text-sm">
                          <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-medium">
                                  {request.title}
                                </span>
                                <span
                                  className={helpStatusClass(request.status)}
                                >
                                  {helpStatusLabel(request.status)}
                                </span>
                                <span
                                  className={priorityClass(request.priority)}
                                >
                                  {priorityLabel(request.priority)}
                                </span>
                              </div>
                              {request.content && (
                                <div className="mt-2 rounded-md bg-zinc-50 px-3 py-2 text-xs leading-5 text-zinc-700">
                                  <div className="mb-1 font-medium text-zinc-500">
                                    學生補充
                                  </div>
                                  <div className="whitespace-pre-wrap">
                                    {request.content}
                                  </div>
                                </div>
                              )}
                              {request.session_messages &&
                                request.session_messages.length > 0 && (
                                  <div className="mt-2 rounded-md border border-zinc-200 bg-white">
                                    <div className="border-b border-zinc-100 px-3 py-2 text-xs font-medium text-zinc-500">
                                      相關聊天紀錄
                                    </div>
                                    <div className="max-h-56 overflow-y-auto divide-y divide-zinc-100">
                                      {request.session_messages.map(
                                        (message, index) => (
                                          <div
                                            key={message.id ?? index}
                                            className="px-3 py-2 text-xs leading-5"
                                          >
                                            <div className="mb-1 flex items-center justify-between gap-2 text-zinc-500">
                                              <span className="font-medium">
                                                {message.role === "user"
                                                  ? "學生"
                                                  : "AI"}
                                              </span>
                                              {message.created_at && (
                                                <span>
                                                  {formatDateTime(
                                                    message.created_at,
                                                  )}
                                                </span>
                                              )}
                                            </div>
                                            <div className="whitespace-pre-wrap text-zinc-700">
                                              {message.content}
                                            </div>
                                          </div>
                                        ),
                                      )}
                                    </div>
                                  </div>
                                )}
                              <div className="mt-2 text-xs text-zinc-500">
                                {formatDateTime(request.updated_at)}
                                {request.username
                                  ? ` · ${request.username}`
                                  : ""}
                              </div>
                            </div>
                            {canManage && (
                              <div className="flex shrink-0 flex-wrap gap-2">
                                {request.status !== "in_progress" && (
                                  <LoadingButton
                                    className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:text-zinc-400"
                                    onClick={() =>
                                      updateHelpRequest(request, "in_progress")
                                    }
                                    loading={
                                      busyAction === `help-status-${request.id}`
                                    }
                                    loadingText="處理中"
                                  >
                                    處理
                                  </LoadingButton>
                                )}
                                {request.status !== "resolved" && (
                                  <LoadingButton
                                    className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2 py-1 text-xs text-emerald-700 hover:bg-emerald-50 disabled:text-zinc-400"
                                    onClick={() =>
                                      updateHelpRequest(request, "resolved")
                                    }
                                    loading={
                                      busyAction === `help-status-${request.id}`
                                    }
                                    loadingText="完成中"
                                  >
                                    結案
                                  </LoadingButton>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                      {helpRequests.length === 0 && (
                        <div className="px-3 py-8 text-sm text-zinc-500">
                          目前沒有求助單
                        </div>
                      )}
                    </div>
                  </section>
                </div>
              )}
              {activeTab === "tasks" && (
                <section className="mx-5 mb-5 mt-5 rounded-lg border border-zinc-200">
                  <div className="flex items-center gap-2 border-b border-zinc-200 px-3 py-2 text-sm font-medium">
                    <ListChecks size={16} className="text-zinc-500" />
                    課程任務
                  </div>
                  {canManage && (
                    <form
                      className="grid gap-3 border-b border-zinc-200 bg-zinc-50 px-3 py-3 md:grid-cols-[1.4fr_160px_1fr_180px_auto]"
                      onSubmit={createAssignment}
                    >
                      <div>
                        <label
                          className="mb-1 block text-xs font-medium text-zinc-500"
                          htmlFor="assignment-title"
                        >
                          任務名稱
                        </label>
                        <input
                          id="assignment-title"
                          className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                          value={assignmentTitle}
                          onChange={(event) =>
                            setAssignmentTitle(event.target.value)
                          }
                        />
                      </div>
                      <div>
                        <label
                          className="mb-1 block text-xs font-medium text-zinc-500"
                          htmlFor="assignment-kind"
                        >
                          類型
                        </label>
                        <select
                          id="assignment-kind"
                          className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                          value={assignmentKind}
                          onChange={(event) => {
                            const nextKind = event.target
                              .value as CourseAssignmentItem["kind"];
                            setAssignmentKind(nextKind);
                            if (!assignmentNeedsDocument(nextKind)) {
                              setAssignmentDocId("");
                            }
                            if (nextKind !== "quiz") setAssignmentQuizId("");
                          }}
                        >
                          <option value="custom">自訂</option>
                          <option value="quiz">測驗</option>
                          <option value="read_summary">閱讀摘要</option>
                          <option value="note">筆記</option>
                          <option value="flashcards">閃卡</option>
                        </select>
                      </div>
                      {assignmentKind === "quiz" ? (
                        <div>
                          <label
                            className="mb-1 block text-xs font-medium text-zinc-500"
                            htmlFor="assignment-quiz"
                          >
                            測驗
                          </label>
                          <select
                            id="assignment-quiz"
                            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                            value={assignmentQuizId}
                            onChange={(event) =>
                              setAssignmentQuizId(event.target.value)
                            }
                          >
                            <option value="">選擇測驗</option>
                            {courseQuizzes.map((quiz) => (
                              <option key={quiz.id} value={quiz.id}>
                                {quiz.course_publication?.title ?? quiz.title}
                              </option>
                            ))}
                          </select>
                        </div>
                      ) : (
                        <div>
                          <label
                            className="mb-1 block text-xs font-medium text-zinc-500"
                            htmlFor="assignment-doc"
                          >
                            文件
                          </label>
                          <select
                            id="assignment-doc"
                            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                            value={assignmentDocId}
                            onChange={(event) =>
                              setAssignmentDocId(event.target.value)
                            }
                            disabled={!assignmentNeedsDocument(assignmentKind)}
                          >
                            <option value="">
                              {assignmentNeedsDocument(assignmentKind)
                                ? "選擇文件"
                                : "不需文件"}
                            </option>
                            {(selected.documents ?? []).map((doc) => (
                              <option key={doc.id} value={doc.id}>
                                {doc.filename}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      <div>
                        <label
                          className="mb-1 block text-xs font-medium text-zinc-500"
                          htmlFor="assignment-due"
                        >
                          截止時間
                        </label>
                        <input
                          id="assignment-due"
                          className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                          type="datetime-local"
                          value={assignmentDueAt}
                          onChange={(event) =>
                            setAssignmentDueAt(event.target.value)
                          }
                        />
                      </div>
                      <div className="flex items-end">
                        <LoadingButton
                          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                          loading={busyAction === "create-assignment"}
                          loadingText="新增中"
                          icon={<Plus size={16} />}
                        >
                          新增
                        </LoadingButton>
                      </div>
                      <textarea
                        className="md:col-span-5 min-h-16 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                        value={assignmentDescription}
                        onChange={(event) =>
                          setAssignmentDescription(event.target.value)
                        }
                        placeholder="任務說明"
                      />
                    </form>
                  )}
                  <div className="divide-y divide-zinc-100">
                    {assignments.map((assignment) => {
                      const action = assignmentAction(assignment);
                      return (
                        <div
                          key={assignment.id}
                          className="flex flex-col gap-3 px-3 py-3 text-sm lg:flex-row lg:items-center lg:justify-between"
                        >
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="truncate font-medium">
                                {assignment.title}
                              </span>
                              <span className="rounded-md bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600">
                                {assignmentKindLabel(assignment.kind)}
                              </span>
                              <span
                                className={assignmentCompletionClass(
                                  assignment.completion.status,
                                )}
                              >
                                {assignmentCompletionLabel(
                                  assignment.completion.status,
                                )}
                              </span>
                            </div>
                            <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-500">
                              {assignment.due_at && (
                                <span className="inline-flex items-center gap-1">
                                  <CalendarClock size={13} />
                                  {formatDateTime(assignment.due_at)}
                                </span>
                              )}
                              {assignment.doc_filename && (
                                <span>{assignment.doc_filename}</span>
                              )}
                              {assignment.quiz_title && (
                                <span>{assignment.quiz_title}</span>
                              )}
                              {assignment.completion.score !== null && (
                                <span>
                                  分數{" "}
                                  {Math.round(
                                    Number(assignment.completion.score) * 100,
                                  )}
                                  %
                                </span>
                              )}
                            </div>
                            {assignment.description && (
                              <div className="mt-2 text-xs leading-5 text-zinc-600">
                                {assignment.description}
                              </div>
                            )}
                          </div>
                          <div className="flex shrink-0 flex-wrap items-center gap-2">
                            {assignment.kind === "custom" ? (
                              <LoadingButton
                                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                                onClick={() => submitAssignment(assignment)}
                                loading={
                                  busyAction ===
                                  `submit-assignment-${assignment.id}`
                                }
                                loadingText="完成中"
                                icon={<CheckCircle2 size={14} />}
                                disabled={
                                  assignment.completion.status ===
                                    "completed" ||
                                  assignment.completion.status === "late"
                                }
                              >
                                標記完成
                              </LoadingButton>
                            ) : action ? (
                              <Link
                                className="inline-flex w-fit items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-medium text-white hover:bg-indigo-700"
                                to={action.href}
                              >
                                <ListChecks size={14} />
                                {action.label}
                              </Link>
                            ) : null}
                            {canManage && (
                              <LoadingButton
                                className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-2 text-xs text-red-600 hover:bg-red-50 disabled:text-zinc-400"
                                onClick={() => deleteAssignment(assignment)}
                                loading={
                                  busyAction ===
                                  `delete-assignment-${assignment.id}`
                                }
                                loadingText="刪除中"
                                icon={<Trash2 size={14} />}
                              >
                                刪除
                              </LoadingButton>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    {assignments.length === 0 && (
                      <div className="px-3 py-8 text-sm text-zinc-500">
                        目前沒有課程任務
                      </div>
                    )}
                  </div>
                </section>
              )}
              {activeTab === "tasks" && (
                <section className="mx-5 mb-5 rounded-lg border border-zinc-200">
                  <div className="flex items-center gap-2 border-b border-zinc-200 px-3 py-2 text-sm font-medium">
                    <ListChecks size={16} className="text-zinc-500" />
                    課程測驗
                  </div>
                  <div className="divide-y divide-zinc-100">
                    {courseQuizzes.map((quiz) => (
                      <div
                        key={quiz.id}
                        className="flex flex-col gap-3 px-3 py-3 text-sm sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="min-w-0">
                          <div className="truncate font-medium">
                            {quiz.course_publication?.title ?? quiz.title}
                          </div>
                          <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-500">
                            <span>{quiz.questions.length} 題</span>
                            {quiz.course_publication?.available_from && (
                              <span>
                                開放{" "}
                                {formatDateTime(
                                  quiz.course_publication.available_from,
                                )}
                              </span>
                            )}
                            {quiz.course_publication?.due_at && (
                              <span>
                                截止{" "}
                                {formatDateTime(quiz.course_publication.due_at)}
                              </span>
                            )}
                            {quiz.course_publication?.attempt_limit && (
                              <span>
                                最多 {quiz.course_publication.attempt_limit} 次
                              </span>
                            )}
                            {quiz.latest_attempt ? (
                              <span className="text-emerald-700">
                                已完成 ·{" "}
                                {Math.round(
                                  Number(quiz.latest_attempt.total_score ?? 0) *
                                    100,
                                )}
                                %
                              </span>
                            ) : (
                              <span className="text-amber-700">待完成</span>
                            )}
                          </div>
                        </div>
                        <Link
                          className="inline-flex w-fit items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-medium text-white hover:bg-indigo-700"
                          to={`/quiz/${quiz.id}`}
                        >
                          <ListChecks size={14} />
                          {quiz.latest_attempt ? "查看測驗" : "開始測驗"}
                        </Link>
                      </div>
                    ))}
                    {courseQuizzes.length === 0 && (
                      <div className="px-3 py-8 text-sm text-zinc-500">
                        目前沒有已發布的課程測驗
                      </div>
                    )}
                  </div>
                </section>
              )}
              {canManage && activeTab === "question-bank" && (
                <section className="mx-5 mb-5 mt-5 rounded-lg border border-zinc-200">
                  <div className="flex items-center justify-between gap-2 border-b border-zinc-200 px-3 py-2">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <ListChecks size={16} className="text-zinc-500" />
                      題庫審題
                    </div>
                    <div className="text-xs text-zinc-500">
                      已核准{" "}
                      {
                        questionBank.filter(
                          (item) => item.status === "approved",
                        ).length
                      }
                      /{questionBank.length}
                    </div>
                  </div>
                  <div className="max-h-[520px] overflow-y-auto divide-y divide-zinc-100">
                    {questionBank.map((item) => (
                      <div key={item.id} className="px-3 py-3 text-sm">
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className={questionReviewClass(item.status)}
                              >
                                {questionReviewLabel(item.status)}
                              </span>
                              <span className="text-xs text-zinc-500">
                                {item.course_quiz_title} · 第{" "}
                                {item.question_index + 1} 題
                              </span>
                              {item.question_type && (
                                <span className="rounded-md bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600">
                                  {item.question_type}
                                </span>
                              )}
                            </div>
                            <div className="mt-2 font-medium leading-6">
                              {questionText(item.question)}
                            </div>
                            {questionOptions(item.question).length > 0 && (
                              <div className="mt-2 grid gap-1 text-xs text-zinc-600 sm:grid-cols-2">
                                {questionOptions(item.question).map(
                                  (option, index) => (
                                    <div
                                      key={`${item.id}-${index}`}
                                      className="rounded-md bg-zinc-50 px-2 py-1"
                                    >
                                      {option}
                                    </div>
                                  ),
                                )}
                              </div>
                            )}
                            <div className="mt-2 flex flex-wrap gap-2 text-xs text-zinc-500">
                              {item.question.answer !== undefined && (
                                <span>
                                  答案：{String(item.question.answer)}
                                </span>
                              )}
                              {item.question.source_page && (
                                <span>頁碼：{item.question.source_page}</span>
                              )}
                              {item.reviewed_at && (
                                <span>
                                  審核：{formatDateTime(item.reviewed_at)}
                                </span>
                              )}
                            </div>
                            {item.question.explanation && (
                              <div className="mt-2 rounded-md bg-indigo-50 px-3 py-2 text-xs leading-5 text-indigo-800">
                                {String(item.question.explanation)}
                              </div>
                            )}
                          </div>
                          <div className="flex shrink-0 flex-wrap gap-2">
                            {item.status !== "approved" && (
                              <LoadingButton
                                className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2 py-1 text-xs text-emerald-700 hover:bg-emerald-50 disabled:text-zinc-400"
                                onClick={() =>
                                  updateQuestionReview(item, "approved")
                                }
                                loading={
                                  busyAction === `review-question-${item.id}`
                                }
                                loadingText="核准中"
                              >
                                核准
                              </LoadingButton>
                            )}
                            {item.status !== "rejected" && (
                              <LoadingButton
                                className="inline-flex items-center gap-1 rounded-lg border border-amber-200 px-2 py-1 text-xs text-amber-700 hover:bg-amber-50 disabled:text-zinc-400"
                                onClick={() =>
                                  updateQuestionReview(item, "rejected")
                                }
                                loading={
                                  busyAction === `review-question-${item.id}`
                                }
                                loadingText="退回中"
                              >
                                退回
                              </LoadingButton>
                            )}
                            {item.status !== "draft" && (
                              <LoadingButton
                                className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:text-zinc-400"
                                onClick={() =>
                                  updateQuestionReview(item, "draft")
                                }
                                loading={
                                  busyAction === `review-question-${item.id}`
                                }
                                loadingText="重設中"
                              >
                                草稿
                              </LoadingButton>
                            )}
                            <LoadingButton
                              className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:text-zinc-400"
                              onClick={() =>
                                updateQuestionReview(item, "archived")
                              }
                              loading={
                                busyAction === `review-question-${item.id}`
                              }
                              loadingText="封存中"
                            >
                              封存
                            </LoadingButton>
                          </div>
                        </div>
                      </div>
                    ))}
                    {questionBank.length === 0 && (
                      <div className="px-3 py-8 text-sm text-zinc-500">
                        發布課程測驗後會自動建立題庫
                      </div>
                    )}
                  </div>
                </section>
              )}
              {activeTab === "materials" && (
                <section className="mx-5 mb-5 mt-5 rounded-lg border border-zinc-200">
                  <div className="border-b border-zinc-200 px-3 py-3">
                    <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <FileText size={16} className="text-zinc-500" />
                        課程教材
                        <span className="text-xs font-normal text-zinc-500">
                          已選 {selectedReadyMaterialIds.length} /{" "}
                          {readyCourseDocuments.length}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          type="button"
                          className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                          onClick={() =>
                            setSelectedMaterialIds(
                              readyCourseDocuments.map((doc) => doc.id),
                            )
                          }
                          disabled={readyCourseDocuments.length === 0}
                        >
                          全選教材
                        </button>
                        <button
                          type="button"
                          className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                          onClick={() => setSelectedMaterialIds([])}
                        >
                          清空
                        </button>
                        {materialActionDocIds.length > 0 ? (
                          <>
                            <Link
                              className="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700"
                              to={scopedLearningPath(
                                "/chat",
                                selected.id,
                                materialActionDocIds,
                              )}
                            >
                              <MessageSquareText size={13} />
                              整課問答
                            </Link>
                            <Link
                              className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                              to={scopedLearningPath(
                                "/quiz/generate",
                                selected.id,
                                materialActionDocIds,
                                canManage ? { publish: "1" } : undefined,
                              )}
                            >
                              <ListChecks size={13} />
                              {canManage ? "整課出題" : "整課測驗"}
                            </Link>
                            <Link
                              className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                              to={scopedLearningPath(
                                "/flashcards",
                                selected.id,
                                materialActionDocIds,
                              )}
                            >
                              <BrainCircuit size={13} />
                              整課閃卡
                            </Link>
                          </>
                        ) : (
                          <span className="text-xs text-zinc-400">
                            尚無可用教材
                          </span>
                        )}
                      </div>
                    </div>
                    {selectedReadyMaterialIds.length === 0 &&
                      readyCourseDocuments.length > 0 && (
                        <div className="mt-2 text-xs text-zinc-500">
                          未選教材時，整課操作會使用全部可用教材。
                        </div>
                      )}
                  </div>
                  <div className="divide-y divide-zinc-100 px-3">
                    {(selected.documents ?? []).map((doc) => (
                      <div
                        key={doc.id}
                        className="flex flex-col gap-2 py-3 text-sm sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="flex min-w-0 items-start gap-2">
                          {doc.course_status !== "removed" &&
                            doc.status === "ready" && (
                              <input
                                className="mt-1"
                                type="checkbox"
                                checked={selectedMaterialIds.includes(doc.id)}
                                onChange={(event) => {
                                  setSelectedMaterialIds((current) =>
                                    event.target.checked
                                      ? [...current, doc.id]
                                      : current.filter(
                                          (item) => item !== doc.id,
                                        ),
                                  );
                                }}
                                aria-label={`選取教材 ${doc.filename}`}
                              />
                            )}
                          <div className="min-w-0">
                            <div className="truncate font-medium">
                              {doc.filename}
                            </div>
                            <div className="text-xs text-zinc-500">
                              {doc.status}
                              {doc.course_status === "removed"
                                ? " · 已移除"
                                : ""}
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {doc.course_status !== "removed" &&
                            doc.status === "ready" && (
                              <>
                                <Link
                                  className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                                  to={scopedLearningPath("/chat", selected.id, [
                                    doc.id,
                                  ])}
                                >
                                  <MessageSquareText size={13} />
                                  對話
                                </Link>
                                <Link
                                  className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                                  to={`/summary/${doc.id}`}
                                >
                                  <BookOpen size={13} />
                                  摘要
                                </Link>
                                <Link
                                  className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                                  to={`/mindmap/${doc.id}`}
                                >
                                  <Network size={13} />
                                  心智圖
                                </Link>
                                <Link
                                  className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                                  to={scopedLearningPath(
                                    "/flashcards",
                                    selected.id,
                                    [doc.id],
                                  )}
                                >
                                  <BrainCircuit size={13} />
                                  閃卡
                                </Link>
                                <Link
                                  className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                                  to={`/notes?doc=${doc.id}`}
                                >
                                  <NotebookPen size={13} />
                                  筆記
                                </Link>
                              </>
                            )}
                          {canManage &&
                            doc.course_status !== "removed" &&
                            doc.status === "ready" && (
                              <Link
                                className="rounded-md border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                                to={scopedLearningPath(
                                  "/quiz/generate",
                                  selected.id,
                                  [doc.id],
                                  { publish: "1" },
                                )}
                              >
                                發布測驗
                              </Link>
                            )}
                          {canManage && doc.course_status !== "removed" && (
                            <LoadingButton
                              className="inline-flex items-center gap-1 text-xs text-red-600 disabled:text-zinc-400"
                              onClick={() => removeDocument(doc.id)}
                              loading={
                                busyAction === `remove-document-${doc.id}`
                              }
                              loadingText="移除中"
                            >
                              移除
                            </LoadingButton>
                          )}
                        </div>
                      </div>
                    ))}
                    {(selected.documents ?? []).length === 0 && (
                      <div className="py-8 text-sm text-zinc-500">
                        尚無課程文件
                      </div>
                    )}
                  </div>
                </section>
              )}
              {activeTab === "overview" && quizSummary.length > 0 && (
                <section className="mx-5 mb-5 rounded-lg border border-zinc-200">
                  <div className="border-b border-zinc-200 px-3 py-2 text-sm font-medium">
                    測驗弱點
                  </div>
                  <div className="divide-y divide-zinc-100">
                    {quizSummary.map((quiz) => (
                      <div
                        key={quiz.course_quiz_id}
                        className="px-3 py-3 text-sm"
                      >
                        <div className="flex flex-wrap justify-between gap-2">
                          <div className="font-medium">{quiz.title}</div>
                          <div className="text-xs text-zinc-500">
                            提交 {quiz.submission_count}/{quiz.student_count} ·
                            平均 {Math.round(quiz.score_avg * 100)}%
                          </div>
                        </div>
                        {quiz.weak_items.slice(0, 3).map((item) => (
                          <div
                            key={String(item.question_index)}
                            className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800"
                          >
                            第 {Number(item.question_index) + 1} 題答對率{" "}
                            {Math.round(Number(item.correct_rate ?? 0) * 100)}
                            %：{String(item.question ?? "")}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
          ) : (
            <div className="flex min-h-[360px] items-center justify-center px-6 py-16 text-center">
              <div>
                <BookOpen size={32} className="mx-auto text-zinc-300" />
                <div className="mt-3 text-sm font-medium text-zinc-700">
                  選擇或建立課程
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function parseCourseTab(value: string | null): CourseTab | null {
  if (
    value === "overview" ||
    value === "materials" ||
    value === "tasks" ||
    value === "interaction" ||
    value === "people" ||
    value === "question-bank"
  ) {
    return value;
  }
  return null;
}

function normalizeCourseTab(tab: CourseTab, course: CourseItem): CourseTab {
  if (
    tab === "question-bank" &&
    course.role !== "instructor" &&
    course.role !== "ta"
  ) {
    return "overview";
  }
  return tab;
}

function coursePath(courseId: string, tab: CourseTab) {
  const params = new URLSearchParams({ course: courseId });
  if (tab !== "overview") params.set("tab", tab);
  return `/courses?${params.toString()}`;
}

function scopedLearningPath(
  path: string,
  courseId: string,
  docIds: string[],
  extra?: Record<string, string>,
) {
  const params = new URLSearchParams({ course: courseId });
  if (docIds.length === 1) {
    params.set("doc", docIds[0]);
  } else if (docIds.length > 1) {
    params.set("docs", docIds.join(","));
  }
  Object.entries(extra ?? {}).forEach(([key, value]) => params.set(key, value));
  return `${path}?${params.toString()}`;
}

function riskLabel(risk: string) {
  if (risk === "high") return "高風險";
  if (risk === "medium") return "待關注";
  return "正常";
}

function SummaryMetric({
  label,
  value,
  detail,
}: {
  label: string;
  value: number;
  detail: string;
}) {
  return (
    <div className="min-w-0 border-l border-zinc-200 pl-3 first:border-l-0 first:pl-0">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 flex items-end justify-between gap-2">
        <div className="text-xl font-semibold text-zinc-900">{value}</div>
        <div className="truncate text-xs text-zinc-500">{detail}</div>
      </div>
    </div>
  );
}

function riskClass(risk: string) {
  const base = "rounded-md px-1.5 py-0.5";
  if (risk === "high") return `${base} bg-red-50 text-red-600`;
  if (risk === "medium") return `${base} bg-amber-50 text-amber-700`;
  return `${base} bg-emerald-50 text-emerald-700`;
}

function assignmentNeedsDocument(kind: string) {
  return ["read_summary", "note", "flashcards"].includes(kind);
}

function buildUpcomingDeadlines(
  assignments: CourseAssignmentItem[],
  quizzes: QuizItem[],
) {
  const items = [
    ...assignments
      .filter((assignment) => assignment.due_at)
      .map((assignment) => ({
        id: assignment.id,
        kind: "assignment",
        kindLabel: "任務",
        title: assignment.title,
        due_at: assignment.due_at as string,
        href: assignmentAction(assignment)?.href ?? "#",
      })),
    ...quizzes
      .filter((quiz) => quiz.course_publication?.due_at)
      .map((quiz) => ({
        id: quiz.id,
        kind: "quiz",
        kindLabel: "測驗",
        title: quiz.course_publication?.title ?? quiz.title,
        due_at: quiz.course_publication?.due_at as string,
        href: `/quiz/${quiz.id}`,
      })),
  ];
  return items
    .filter((item) => !Number.isNaN(new Date(item.due_at).getTime()))
    .sort(
      (left, right) =>
        new Date(left.due_at).getTime() - new Date(right.due_at).getTime(),
    )
    .slice(0, 3);
}

function deadlineLabel(value: string) {
  const diffMs = new Date(value).getTime() - Date.now();
  if (Number.isNaN(diffMs)) return "期限";
  if (diffMs < 0) return "已逾期";
  const days = Math.ceil(diffMs / 86_400_000);
  if (days <= 1) return "24 小時內";
  if (days <= 7) return `${days} 天`;
  return "之後";
}

function deadlineClass(value: string) {
  const base = "shrink-0 rounded-md px-2 py-0.5 text-xs";
  const diffMs = new Date(value).getTime() - Date.now();
  if (Number.isNaN(diffMs)) return `${base} bg-zinc-100 text-zinc-600`;
  if (diffMs < 0) return `${base} bg-red-50 text-red-600`;
  if (diffMs <= 86_400_000) return `${base} bg-amber-50 text-amber-700`;
  return `${base} bg-indigo-50 text-indigo-700`;
}

function normalizeDateTimeInput(value: string) {
  if (!value) return null;
  return new Date(value).toISOString();
}

function assignmentKindLabel(kind: string) {
  if (kind === "quiz") return "測驗";
  if (kind === "read_summary") return "閱讀摘要";
  if (kind === "note") return "筆記";
  if (kind === "flashcards") return "閃卡";
  return "自訂";
}

function assignmentCompletionLabel(status: string) {
  if (status === "completed") return "已完成";
  if (status === "late") return "逾期完成";
  if (status === "overdue") return "已逾期";
  return "待完成";
}

function assignmentCompletionClass(status: string) {
  const base = "rounded-md px-2 py-0.5 text-xs";
  if (status === "completed") return `${base} bg-emerald-50 text-emerald-700`;
  if (status === "late") return `${base} bg-amber-50 text-amber-700`;
  if (status === "overdue") return `${base} bg-red-50 text-red-600`;
  return `${base} bg-zinc-100 text-zinc-600`;
}

function assignmentAction(assignment: CourseAssignmentItem) {
  if (assignment.kind === "quiz" && assignment.quiz_id) {
    return { href: `/quiz/${assignment.quiz_id}`, label: "開始測驗" };
  }
  if (assignment.kind === "read_summary" && assignment.doc_id) {
    return { href: `/summary/${assignment.doc_id}`, label: "閱讀摘要" };
  }
  if (assignment.kind === "note" && assignment.doc_id) {
    return { href: `/notes?doc=${assignment.doc_id}`, label: "寫筆記" };
  }
  if (assignment.kind === "flashcards" && assignment.doc_id) {
    return { href: `/flashcards?doc=${assignment.doc_id}`, label: "練閃卡" };
  }
  return null;
}

function questionText(question: Record<string, any>) {
  return String(question.question ?? question.prompt ?? question.title ?? "");
}

function questionOptions(question: Record<string, any>) {
  const raw = question.options;
  if (Array.isArray(raw)) return raw.map((item) => String(item));
  if (raw && typeof raw === "object") {
    return Object.entries(raw).map(
      ([key, value]) => `${key}. ${String(value)}`,
    );
  }
  return [];
}

function questionReviewLabel(status: string) {
  if (status === "approved") return "已核准";
  if (status === "rejected") return "退回";
  if (status === "archived") return "封存";
  return "草稿";
}

function questionReviewClass(status: string) {
  const base = "rounded-md px-2 py-0.5 text-xs";
  if (status === "approved") return `${base} bg-emerald-50 text-emerald-700`;
  if (status === "rejected") return `${base} bg-amber-50 text-amber-700`;
  if (status === "archived") return `${base} bg-zinc-100 text-zinc-600`;
  return `${base} bg-indigo-50 text-indigo-700`;
}

function helpStatusLabel(status: string) {
  if (status === "in_progress") return "處理中";
  if (status === "resolved") return "已結案";
  return "待處理";
}

function helpStatusClass(status: string) {
  const base = "rounded-md px-2 py-0.5 text-xs";
  if (status === "resolved") return `${base} bg-emerald-50 text-emerald-700`;
  if (status === "in_progress") return `${base} bg-indigo-50 text-indigo-700`;
  return `${base} bg-amber-50 text-amber-700`;
}

function priorityLabel(priority: string) {
  if (priority === "high") return "高";
  if (priority === "low") return "低";
  return "一般";
}

function priorityClass(priority: string) {
  const base = "rounded-md px-2 py-0.5 text-xs";
  if (priority === "high") return `${base} bg-red-50 text-red-600`;
  if (priority === "low") return `${base} bg-zinc-100 text-zinc-600`;
  return `${base} bg-zinc-100 text-zinc-700`;
}

function safeFilename(value: string) {
  return value.trim().replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]+/g, "_") || "course";
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 16);
  return date.toLocaleString(undefined, {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
