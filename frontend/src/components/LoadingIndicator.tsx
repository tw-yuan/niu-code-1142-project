import { Loader2 } from 'lucide-react';

interface Props {
  message?: string;
}

export default function LoadingIndicator({ message = '載入中...' }: Props) {
  return (
    <div className="flex items-center justify-center gap-2 p-8">
      <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
      <span className="text-gray-600">{message}</span>
    </div>
  );
}
