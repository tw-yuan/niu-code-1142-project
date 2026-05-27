import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileText, FileSpreadsheet, File } from 'lucide-react';

const ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt', '.md'],
  'text/markdown': ['.md'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'text/csv': ['.csv'],
};

interface Props {
  files: File[];
  onFilesChange: (files: File[]) => void;
  label: string;
  maxSizeMB?: number;
}

function getFileIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return <FileText className="w-4 h-4 text-red-500" />;
  if (ext === 'docx') return <FileText className="w-4 h-4 text-blue-500" />;
  if (ext === 'xlsx' || ext === 'csv') return <FileSpreadsheet className="w-4 h-4 text-green-500" />;
  return <File className="w-4 h-4 text-gray-500" />;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileUploader({ files, onFilesChange, label, maxSizeMB = 10 }: Props) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      onFilesChange([...files, ...accepted]);
    },
    [files, onFilesChange]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxSize: maxSizeMB * 1024 * 1024,
  });

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition ${
          isDragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm text-gray-600">拖放檔案至此，或點擊選擇檔案</p>
        <p className="text-xs text-gray-400 mt-1">
          支援 PDF、DOCX、TXT、MD、XLSX、CSV（最大 {maxSizeMB} MB）
        </p>
      </div>
      {files.length > 0 && (
        <ul className="mt-3 space-y-2">
          {files.map((f, i) => (
            <li key={i} className="flex items-center gap-2 bg-gray-50 rounded px-3 py-2 text-sm">
              {getFileIcon(f.name)}
              <span className="flex-1 truncate">{f.name}</span>
              <span className="text-gray-400 text-xs">{formatSize(f.size)}</span>
              <button onClick={() => removeFile(i)} className="text-gray-400 hover:text-red-500">
                <X className="w-4 h-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
