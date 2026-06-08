import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import ChatBubble from "../components/ChatBubble";
import { getSession } from "../api/sessions";
import type { Message, SessionDetail } from "../api/sessions";

export default function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!sessionId) return;
    getSession(Number(sessionId)).then((s) => {
      setSession(s);
      setMessages(s.messages);
    });
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  async function sendMessage() {
    if (!input.trim() || streaming || !sessionId) return;
    const text = input.trim();
    setInput("");
    const userMsg: Message = {
      id: Date.now(),
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setStreamingText("");

    try {
      const resp = await fetch(`/api/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ content: text }),
      });

      if (!resp.ok || !resp.body) throw new Error("Request failed");

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let full = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const payload = line.slice(6);
            if (payload === "[DONE]") break;
            if (payload.startsWith("[ERROR]")) {
              full += payload;
              break;
            }
            const delta = payload.replace(/\\n/g, "\n");
            full += delta;
            setStreamingText(full);
          }
        }
      }

      const assistantMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: full,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setStreamingText("");
    } catch {
      setStreamingText("");
    } finally {
      setStreaming(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <AppHeader />
      <div className="flex flex-1 overflow-hidden max-w-5xl mx-auto w-full px-4 py-4 gap-4">
        {/* Sidebar */}
        <div className="w-60 flex-shrink-0">
          <div className="bg-white border border-gray-200 rounded-xl p-4 sticky top-20">
            <button
              onClick={() => session && navigate(`/documents/${session.document_id}`)}
              className="text-xs text-gray-400 hover:text-indigo-500 mb-3 flex items-center gap-1"
            >
              ← 返回方向選擇
            </button>
            {session && (
              <>
                <div className="text-xs text-gray-400 mb-1">講義</div>
                <div className="text-sm font-medium text-gray-700 truncate mb-3">
                  {session.document_original_filename}
                </div>
                <div className="text-xs text-gray-400 mb-1">學習方向</div>
                <div className="flex items-center gap-1.5">
                  <span className="text-lg">{session.direction_emoji}</span>
                  <span className="text-sm font-semibold text-indigo-700">
                    {session.direction_label}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4">
            {messages.length === 0 && !streaming && (
              <div className="text-center text-gray-400 py-16">
                <div className="text-3xl mb-3">{session?.direction_emoji || "💬"}</div>
                <p className="text-sm">
                  你正在使用「{session?.direction_label}」模式<br />
                  輸入你的問題開始學習吧！
                </p>
              </div>
            )}
            {messages.map((msg) => (
              <ChatBubble key={msg.id} message={msg} />
            ))}
            {streamingText && (
              <ChatBubble
                message={{ id: -1, role: "assistant", content: streamingText, created_at: "" }}
              />
            )}
            {streaming && !streamingText && (
              <div className="flex justify-start mb-4">
                <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-sm mr-2">📚</div>
                <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-tl-sm text-gray-400 text-sm">
                  思考中...
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-gray-100 p-3 flex gap-2 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="輸入問題，Enter 送出（Shift+Enter 換行）"
              rows={1}
              className="flex-1 resize-none border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 leading-relaxed max-h-32 overflow-y-auto"
              style={{ minHeight: "40px" }}
              disabled={streaming}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || streaming}
              className="bg-indigo-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-40 flex-shrink-0"
            >
              送出
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
