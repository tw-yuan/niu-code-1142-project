import { AlertTriangle, X } from 'lucide-react';

interface Props {
  message: string;
  onClose?: () => void;
}

export default function ErrorAlert({ message, onClose }: Props) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
      <p className="text-red-700 text-sm flex-1">{message}</p>
      {onClose && (
        <button onClick={onClose} className="text-red-400 hover:text-red-600">
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
