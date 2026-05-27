import { useState } from 'react';
import { Copy, Check, AlertTriangle, FileText } from 'lucide-react';
import type { Deliverable, StructuredOutput } from '../types/task';

interface Props {
  data: StructuredOutput;
}

export default function ResultViewer({ data }: Props) {
  const [copied, setCopied] = useState(false);

  const formatContent = (content: Deliverable['content']) => {
    if (typeof content === 'string') return content;
    return JSON.stringify(content, null, 2) ?? '';
  };

  const copyText = () => {
    const text = [
      `# ${data.title}`,
      `\n## 作業需求摘要\n${data.assignment_summary}`,
      data.explanation ? `\n## AI 講解\n${data.explanation}` : '',
      data.requirements_breakdown?.length ? `\n## 需求拆解\n${data.requirements_breakdown.map((r, i) => `${i + 1}. ${r}`).join('\n')}` : '',
      data.answer_outline?.length ? `\n## 回答大綱\n${data.answer_outline.map((r, i) => `${i + 1}. ${r}`).join('\n')}` : '',
      data.generated_draft ? `\n## 畫面摘要\n${data.generated_draft}` : '',
      data.deliverables?.length
        ? `\n## 產出檔案\n${data.deliverables.map((d) => `### ${d.title}\n格式：${d.format}\n檔名：${d.filename}\n用途：${d.purpose}\n\n${formatContent(d.content)}`).join('\n\n')}`
        : '',
      data.references?.length ? `\n## 引用來源\n${data.references.map((r) => `- ${r.source_name}：${r.quote_or_summary}`).join('\n')}` : '',
      data.academic_integrity_notice ? `\n## 提醒\n${data.academic_integrity_notice}` : '',
    ].filter(Boolean).join('\n');

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      {data.academic_integrity_notice && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <p className="text-sm text-amber-700">{data.academic_integrity_notice}</p>
        </div>
      )}

      {/* Title & summary */}
      <div className="bg-white border rounded-lg p-6">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">{data.title}</h2>
          <button
            onClick={copyText}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50"
          >
            {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            {copied ? '已複製' : '複製全文'}
          </button>
        </div>
        <p className="text-gray-600 text-sm">{data.assignment_summary}</p>
      </div>

      {data.explanation && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-700 mb-3">AI 講解</h3>
          <div className="prose prose-sm max-w-none text-gray-600 whitespace-pre-wrap">
            {data.explanation}
          </div>
        </div>
      )}

      {/* Requirements breakdown */}
      {data.requirements_breakdown?.length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-700 mb-3">需求拆解</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
            {data.requirements_breakdown.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ol>
        </div>
      )}

      {/* Answer outline */}
      {data.answer_outline?.length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-700 mb-3">回答大綱</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
            {data.answer_outline.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ol>
        </div>
      )}

      {data.deliverables && data.deliverables.length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-700 mb-3">AI 決定的產出檔案</h3>
          <div className="space-y-3">
            {data.deliverables.map((item, index) => (
              <div key={item.id || index} className="border rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                  <div className="min-w-0">
                    <p className="font-medium text-gray-800">{item.title}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {item.filename} · {item.format.toUpperCase()}
                    </p>
                    <p className="text-sm text-gray-600 mt-2">{item.purpose}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.generated_draft && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-700 mb-3">畫面摘要</h3>
          <div className="prose prose-sm max-w-none text-gray-600 whitespace-pre-wrap">
            {data.generated_draft}
          </div>
        </div>
      )}

      {/* References */}
      {data.references?.length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-700 mb-3">引用來源</h3>
          <div className="space-y-2">
            {data.references.map((ref, i) => (
              <div key={i} className="text-sm border-l-2 border-blue-200 pl-3">
                <p className="font-medium text-gray-700">{ref.source_name}</p>
                <p className="text-gray-500">{ref.quote_or_summary}</p>
                <p className="text-gray-400 text-xs">用於：{ref.used_for}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Limitations */}
      {data.limitations?.length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-700 mb-3">限制說明</h3>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
            {data.limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Human review checklist */}
      {data.human_review_checklist && data.human_review_checklist.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="font-semibold text-blue-700 mb-3">人工確認清單</h3>
          <div className="space-y-2">
            {data.human_review_checklist.map((item, i) => (
              <label key={i} className="flex items-start gap-2 text-sm text-blue-700">
                <input type="checkbox" className="mt-1" />
                <span>{item}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
