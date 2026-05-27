import { CheckCircle, Loader2, AlertCircle } from 'lucide-react';

interface ProgressEvent {
  event_type: string;
  message: string;
}

interface Props {
  events: ProgressEvent[];
  status: string;
}

function getIcon(eventType: string, isLast: boolean, taskStatus: string) {
  if (eventType === 'error') return <AlertCircle className="w-4 h-4 text-red-500" />;
  if (eventType === 'complete') return <CheckCircle className="w-4 h-4 text-green-500" />;
  if (isLast && taskStatus === 'processing') return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
  return <CheckCircle className="w-4 h-4 text-green-400" />;
}

export default function ProgressPanel({ events, status }: Props) {
  if (events.length === 0) return null;

  return (
    <div className="bg-white border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">處理進度</h3>
      <div className="space-y-2">
        {events.map((e, i) => (
          <div key={i} className="flex items-center gap-2">
            {getIcon(e.event_type, i === events.length - 1, status)}
            <span className={`text-sm ${e.event_type === 'error' ? 'text-red-600' : 'text-gray-600'}`}>
              {e.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
