import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import FileUploader from "../components/FileUploader";
import { listDocuments, deleteDocument } from "../api/documents";
import type { Document } from "../api/documents";

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("zh-TW", {
    year: "numeric", month: "long", day: "numeric",
  });
}

export default function HomePage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    listDocuments()
      .then(setDocs)
      .finally(() => setLoading(false));
  }, []);

  function handleUploaded(doc: Document) {
    setDocs((prev) => [doc, ...prev]);
    setShowUpload(false);
    navigate(`/documents/${doc.id}`);
  }

  async function handleDelete(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("確定要刪除這份講義？")) return;
    await deleteDocument(id);
    setDocs((prev) => prev.filter((d) => d.id !== id));
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-800">我的講義</h2>
          <button
            onClick={() => setShowUpload((v) => !v)}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            + 上傳新講義
          </button>
        </div>

        {showUpload && (
          <div className="mb-6">
            <FileUploader onUploaded={handleUploaded} />
          </div>
        )}

        {loading ? (
          <div className="text-center text-gray-400 py-16">載入中...</div>
        ) : docs.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-5xl mb-4">📭</div>
            <p className="text-gray-500 mb-4">還沒有任何講義</p>
            <button
              onClick={() => setShowUpload(true)}
              className="text-indigo-600 hover:underline text-sm"
            >
              上傳第一份講義
            </button>
          </div>
        ) : (
          <div className="grid gap-3">
            {docs.map((doc) => (
              <div
                key={doc.id}
                onClick={() => navigate(`/documents/${doc.id}`)}
                className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:border-indigo-300 hover:shadow-sm transition-all group"
              >
                <div className="text-2xl">
                  {doc.file_type === "pdf" ? "📕" : doc.file_type === "docx" ? "📘" : doc.file_type === "pptx" ? "📊" : "📄"}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-800 truncate group-hover:text-indigo-700">
                    {doc.original_filename}
                  </div>
                  {(doc.course_name || doc.lesson_topic) && (
                    <div className="mt-0.5 truncate text-xs text-gray-500">
                      {[doc.course_name, doc.lesson_topic].filter(Boolean).join(" · ")}
                    </div>
                  )}
                  <div className="text-xs text-gray-400 mt-0.5">
                    {formatDate(doc.created_at)} · {formatSize(doc.file_size)} · {doc.token_count.toLocaleString()} tokens
                    {doc.index_status === "indexed" && doc.token_count >= 12000 && (
                      <span className="ml-2 text-emerald-500">✓ RAG</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={(e) => handleDelete(doc.id, e)}
                  className="text-gray-300 hover:text-red-400 transition-colors px-2"
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
