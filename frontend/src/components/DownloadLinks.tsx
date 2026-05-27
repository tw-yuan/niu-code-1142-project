import { Download, AlertCircle } from 'lucide-react';
import type { GeneratedFileInfo } from '../types/task';
import { getDownloadUrl } from '../api/tasks';

interface Props {
  taskId: string;
  files: GeneratedFileInfo[];
}

const FORMAT_LABELS: Record<string, string> = {
  txt: '純文字',
  docx: 'Word (.docx)',
  pdf: 'PDF',
  xlsx: 'Excel (.xlsx)',
};

export default function DownloadLinks({ taskId, files }: Props) {
  if (files.length === 0) return null;

  return (
    <div className="bg-white border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">下載檔案</h3>
      <div className="grid grid-cols-2 gap-2">
        {files.map((f) => (
          <div key={f.id}>
            {f.status === 'success' ? (
              <a
                href={getDownloadUrl(taskId, f.id)}
                className="flex items-center gap-2 px-4 py-2 border rounded-lg text-sm text-blue-600 hover:bg-blue-50 transition"
              >
                <Download className="w-4 h-4" />
                {FORMAT_LABELS[f.format] || f.format}
              </a>
            ) : (
              <div className="flex items-center gap-2 px-4 py-2 border border-red-200 rounded-lg text-sm text-red-500">
                <AlertCircle className="w-4 h-4" />
                <span>{FORMAT_LABELS[f.format] || f.format} 產生失敗</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
