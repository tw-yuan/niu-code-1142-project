import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import DirectionCard from "../components/DirectionCard";
import { getDocument, getDirections } from "../api/documents";
import { createSession } from "../api/sessions";
import type { Document, Direction } from "../api/documents";

export default function DocumentPage() {
  const { docId } = useParams<{ docId: string }>();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<Document | null>(null);
  const [directions, setDirections] = useState<Direction[]>([]);
  const [loadingDoc, setLoadingDoc] = useState(true);
  const [loadingDirs, setLoadingDirs] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [starting, setStarting] = useState<string | null>(null);

  useEffect(() => {
    if (!docId) return;
    getDocument(Number(docId))
      .then(setDoc)
      .finally(() => setLoadingDoc(false));
    loadDirections(false);
  }, [docId]);

  async function loadDirections(refresh: boolean) {
    if (!docId) return;
    if (refresh) setRefreshing(true);
    else setLoadingDirs(true);
    try {
      const result = await getDirections(Number(docId), refresh);
      setDirections(result.directions);
    } finally {
      setLoadingDirs(false);
      setRefreshing(false);
    }
  }

  async function handleDirectionClick(dir: Direction) {
    if (!docId) return;
    setStarting(dir.key);
    try {
      const session = await createSession({
        document_id: Number(docId),
        direction_key: dir.key,
        direction_label: dir.label,
        direction_description: dir.description,
        direction_emoji: dir.emoji,
      });
      navigate(`/sessions/${session.id}`, { state: { documentId: Number(docId) } });
    } finally {
      setStarting(null);
    }
  }

  const fixedDirs = directions.filter((d) => !d.is_dynamic);
  const dynamicDirs = directions.filter((d) => d.is_dynamic);

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main className="max-w-3xl mx-auto px-6 py-8">
        <button
          onClick={() => navigate("/")}
          className="text-sm text-gray-400 hover:text-indigo-500 mb-6 flex items-center gap-1"
        >
          ← 返回講義列表
        </button>

        {loadingDoc ? (
          <div className="text-gray-400">載入中...</div>
        ) : doc ? (
          <div className="bg-white border border-gray-200 rounded-xl p-5 mb-8">
            <div className="flex items-start gap-4">
              <div className="text-3xl">
                {doc.file_type === "pdf" ? "📕" : doc.file_type === "docx" ? "📘" : "📄"}
              </div>
              <div>
                <h2 className="font-semibold text-gray-800 text-lg">{doc.original_filename}</h2>
                <p className="text-sm text-gray-400 mt-0.5">
                  {doc.token_count.toLocaleString()} tokens
                  {doc.token_count >= 12000 ? (
                    <span className="ml-2 text-emerald-500">✓ 已建立向量索引</span>
                  ) : (
                    <span className="ml-2 text-blue-400">全文模式</span>
                  )}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-red-500">找不到此文件</p>
        )}

        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-700">選擇學習方向</h3>
          <button
            onClick={() => loadDirections(true)}
            disabled={loadingDirs || refreshing}
            className="text-xs text-gray-400 hover:text-indigo-500 disabled:opacity-40 flex items-center gap-1"
          >
            {refreshing ? "生成中..." : "↻ 重新生成推薦"}
          </button>
        </div>

        {loadingDirs ? (
          <div className="text-gray-400 text-sm">分析講義內容中，請稍候...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {fixedDirs.map((dir) => (
                <div key={dir.key} className={starting === dir.key ? "opacity-50 pointer-events-none" : ""}>
                  <DirectionCard direction={dir} onClick={() => handleDirectionClick(dir)} />
                </div>
              ))}
            </div>

            {dynamicDirs.length > 0 && (
              <>
                <h4 className="text-sm font-medium text-indigo-600 mb-3">✨ 專為這份講義推薦</h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {dynamicDirs.map((dir) => (
                    <div key={dir.key} className={starting === dir.key ? "opacity-50 pointer-events-none" : ""}>
                      <DirectionCard direction={dir} onClick={() => handleDirectionClick(dir)} />
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
