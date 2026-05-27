import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ProgressEventInfo } from '../types/task';

interface Props {
  events: ProgressEventInfo[];
}

export default function DetailedProcessPanel({ events }: Props) {
  const [open, setOpen] = useState(false);

  if (events.length === 0) return null;

  return (
    <div className="border rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <span>查看詳細過程（{events.length} 筆紀錄）</span>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {open && (
        <div className="border-t px-4 py-3 max-h-80 overflow-y-auto">
          <div className="space-y-3">
            {events.map((e) => (
              <div key={e.id} className="text-sm">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-mono ${
                    e.event_type === 'error' ? 'bg-red-100 text-red-600' :
                    e.event_type === 'complete' ? 'bg-green-100 text-green-600' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {e.event_type}
                  </span>
                  <span className="text-gray-500 text-xs">
                    {new Date(e.created_at).toLocaleTimeString('zh-TW')}
                  </span>
                </div>
                <p className="text-gray-700 mt-1">{e.message}</p>
                {e.detail && (
                  <pre className="text-xs bg-gray-50 rounded p-2 mt-1 overflow-x-auto text-gray-500">
                    {JSON.stringify(e.detail, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
