import { useRef, useState } from "react";
import { uploadDocument } from "../api/documents";
import type { Document } from "../api/documents";

interface Props {
  onUploaded: (doc: Document) => void;
}

export default function FileUploader({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<"idle" | "uploading" | "handoff">("idle");
  const [error, setError] = useState("");
  const [courseName, setCourseName] = useState("");
  const [lessonTopic, setLessonTopic] = useState("");
  const [learningGoals, setLearningGoals] = useState("");

  async function handleFile(file: File) {
    setError("");
    setProgress(0);
    setPhase("uploading");
    setUploading(true);
    try {
      const doc = await uploadDocument(file, setProgress, {
        course_name: courseName.trim(),
        lesson_topic: lessonTopic.trim(),
        learning_goals: learningGoals.trim(),
      });
      setPhase("handoff");
      setProgress(100);
      onUploaded(doc);
    } catch (e: unknown) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } };
      const msg = err.response?.data?.detail;
      if (err.response?.status === 413) {
        setError(msg || "檔案太大，請壓縮檔案或調高伺服器上傳限制");
      } else {
        setError(msg || "上傳失敗，請再試一次");
      }
    } finally {
      setUploading(false);
      setPhase("idle");
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <div>
      <div className="mb-3 grid gap-3 sm:grid-cols-2">
        <input
          value={courseName}
          onChange={(e) => setCourseName(e.target.value)}
          placeholder="課程名稱（選填）"
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          disabled={uploading}
        />
        <input
          value={lessonTopic}
          onChange={(e) => setLessonTopic(e.target.value)}
          placeholder="本週主題（選填）"
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          disabled={uploading}
        />
        <textarea
          value={learningGoals}
          onChange={(e) => setLearningGoals(e.target.value)}
          placeholder="教師學習目標或考試範圍（選填）"
          rows={2}
          className="sm:col-span-2 resize-none rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          disabled={uploading}
        />
      </div>
      <div
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
          dragging ? "border-indigo-400 bg-indigo-50 scale-[1.01]" : "border-gray-300 hover:border-indigo-300"
        } ${uploading ? "pointer-events-none border-indigo-300 bg-indigo-50/50" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <div className={`text-4xl mb-3 ${uploading ? "animate-bounce" : ""}`}>{uploading ? "⏳" : "📄"}</div>
        <div className="text-gray-600 font-medium">
          {uploading ? (phase === "handoff" ? "上傳完成，準備解析..." : "上傳中...") : "點擊或拖曳講義到這裡"}
        </div>
        <div className="text-sm text-gray-400 mt-1">支援 PDF、DOCX、PPTX、TXT、MD、JPG、PNG、WebP</div>
        {uploading && (
          <div className="mt-5">
            <div className="h-2 overflow-hidden rounded-full bg-white">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all duration-300"
                style={{ width: `${Math.max(progress, 8)}%` }}
              />
            </div>
            <div className="mt-2 flex justify-between text-xs text-gray-400">
              <span>{phase === "handoff" ? "交給後端背景處理" : "傳送檔案"}</span>
              <span>{progress}%</span>
            </div>
          </div>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.pptx,.txt,.md,.jpg,.jpeg,.png,.webp"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />
      {error && <p className="text-red-500 text-sm mt-2 text-center">{error}</p>}
    </div>
  );
}
