import type { Message } from "../api/sessions";
import Markdown from "./Markdown";

interface Props {
  message: Message;
}

export default function ChatBubble({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-sm mr-2 flex-shrink-0 mt-1">
          📚
        </div>
      )}
      <div
        className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "bg-indigo-600 text-white rounded-tr-sm"
            : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm"
        }`}
      >
        {!isUser && (
          <div className="flex justify-end mb-2">
            <button
              onClick={() => navigator.clipboard?.writeText(message.content)}
              className="text-xs text-gray-300 hover:text-indigo-500"
            >
              複製
            </button>
          </div>
        )}
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <Markdown content={message.content} />
        )}
        {!isUser && message.context_chunks_used && message.context_chunks_used.length > 0 && (
          <details className="mt-3 border-t border-gray-100 pt-2">
            <summary className="cursor-pointer text-xs text-gray-400 hover:text-indigo-500">
              使用的講義片段（{message.context_chunks_used.length}）
            </summary>
            <div className="mt-2 space-y-2">
              {message.context_chunks_used.map((source, index) => (
                <div key={`${source.chunk_index}-${index}`} className="rounded-lg bg-gray-50 p-2 text-xs text-gray-500 whitespace-pre-wrap">
                  <div className="font-medium text-gray-400 mb-1">片段 {Number(source.chunk_index) + 1}</div>
                  {source.snippet || source.text}
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
