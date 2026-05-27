import { useCallback, useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileText, FileSpreadsheet, File as FileIcon, Image } from 'lucide-react';

interface Props {
  files: File[];
  onFilesChange: (files: File[]) => void;
  label: string;
  maxSizeMB?: number;
  disabled?: boolean;
  disabledMessage?: string;
}

function getFileIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return <FileText className="w-4 h-4 text-red-500" />;
  if (ext === 'docx') return <FileText className="w-4 h-4 text-blue-500" />;
  if (ext === 'xlsx' || ext === 'csv') return <FileSpreadsheet className="w-4 h-4 text-green-500" />;
  if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'webp') {
    return <Image className="w-4 h-4 text-purple-500" />;
  }
  return <FileIcon className="w-4 h-4 text-gray-500" />;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileExtension(name: string) {
  const ext = name.includes('.') ? `.${name.split('.').pop()?.toLowerCase()}` : '';
  return ext || '';
}

function normalizePastedFile(file: File, index: number) {
  if (file.name && fileExtension(file.name)) return file;
  const extensionByType: Record<string, string> = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/webp': 'webp',
  };
  const ext = extensionByType[file.type] || 'bin';
  return new File([file], `pasted-file-${Date.now()}-${index}.${ext}`, { type: file.type });
}

export default function FileUploader({
  files,
  onFilesChange,
  label,
  maxSizeMB = 10,
  disabled = false,
  disabledMessage = '目前無法上傳檔案',
}: Props) {
  const [pasteActive, setPasteActive] = useState(false);

  const appendFiles = useCallback(
    (nextFiles: File[]) => {
      if (disabled || nextFiles.length === 0) return;
      const accepted = nextFiles.filter((file) => file.size <= maxSizeMB * 1024 * 1024);
      if (accepted.length > 0) {
        onFilesChange([...files, ...accepted]);
      }
    },
    [disabled, files, maxSizeMB, onFilesChange]
  );

  const onDrop = useCallback(
    (accepted: File[]) => {
      appendFiles(accepted);
    },
    [appendFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize: maxSizeMB * 1024 * 1024,
    disabled,
  });

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  useEffect(() => {
    if (!pasteActive || disabled) return;

    const handlePaste = (event: ClipboardEvent) => {
      const clipboardFiles = Array.from(event.clipboardData?.files || []);
      const itemFiles = Array.from(event.clipboardData?.items || [])
        .filter((item) => item.kind === 'file')
        .map((item) => item.getAsFile())
        .filter((file): file is File => Boolean(file));

      const pastedFiles = (clipboardFiles.length > 0 ? clipboardFiles : itemFiles)
        .map((file, index) => normalizePastedFile(file, index));

      if (pastedFiles.length === 0) return;
      event.preventDefault();
      appendFiles(pastedFiles);
    };

    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [appendFiles, disabled, pasteActive]);

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <div
        {...getRootProps({
          tabIndex: disabled ? -1 : 0,
          onFocus: () => setPasteActive(true),
          onClick: () => setPasteActive(true),
          onBlur: () => setPasteActive(false),
        })}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition ${
          disabled
            ? 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-70'
            : pasteActive
              ? 'border-blue-400 bg-blue-50'
              : isDragActive
              ? 'border-blue-400 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm text-gray-600">
          {disabled ? disabledMessage : '拖放檔案至此，或點擊選擇檔案'}
        </p>
        <p className="text-xs text-gray-400 mt-1">
          可上傳任何檔案格式（最大 {maxSizeMB} MB）；文件、表格與圖片會嘗試解析
        </p>
        {!disabled && (
          <p className="text-xs text-blue-500 mt-1">
            點一下此區塊後可用 Ctrl+V 貼上剪貼簿檔案或圖片
          </p>
        )}
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
