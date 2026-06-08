import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import ChatBubble from "../components/ChatBubble";
import { getSession } from "../api/sessions";
import type { Message, SessionDetail } from "../api/sessions";

const INITIAL_MESSAGES: Record<string, string> = {
  summary: "請根據這份講義內容，生成完整的章節摘要，以條列重點的方式呈現。",
  quiz: "請根據這份講義內容出 5 道測驗題（混合選擇題與問答題），等我作答後再逐題批改。",
  explain: "請先介紹這份講義的主要主題與核心概念，讓我建立整體的理解。",
  qa: "你好！我已讀取這份講義，有什麼想了解的問題嗎？",
};

function getInitialMessage(key: string, label: string): string {
  return INITIAL_MESSAGES[key] ?? `我選擇了「${label}」這個學習方向，請根據講義內容開始輔助我學習。`;
}

// 從串流文字中分離 <think> 思考內容與實際回應
function parseThinking(text: string): { thinking: string; response: string; inThink: boolean } {
  const thinkStart = text.indexOf("<think>");
  const thinkEnd = text.indexOf("</think>");

  if (thinkStart === -1) return { thinking: "", response: text, inThink: false };

  if (thinkEnd === -1) {
    // 思考還在進行中
    return {
      thinking: text.slice(thinkStart + 7),
      response: "",
      inThink: true,
    };
  }

  return {
    thinking: text.slice(thinkStart + 7, thinkEnd),
    response: text.slice(thinkEnd + 8).trimStart(),
    inThink: false,
  };
}

// 逐行解析 SSE，buffer 處理 partial chunk
async function* parseSse(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) yield line.slice(6);
    }
  }
}

// 思考過程元件
function ThinkingBlock({ text, done }: { text: string; done: boolean }) {
  const [open, setOpen] = useState(true);
  if (!text) return null;
  return (
    <div className="mb-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <span className={`transition-transform duration-200 ${open ? "rotate-90" : ""}`}>▶</span>
        {done ? "思考過程" : <span className="animate-pulse">思考中...</span>}
        {text && <span className="text-gray-300">({text.length} 字)</span>}
      </button>
      {open && (
        <div className="mt-1.5 ml-4 pl-3 border-l-2 border-gray-200 text-xs text-gray-400 leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
          {text}
          {!done && <span className="inline-block w-1.5 h-3 bg-gray-300 animate-pulse ml-0.5 align-middle" />}
        </div>
      )}
    </div>
  );
}

// 串流中的 AI 訊息氣泡（含思考過程）
function StreamingBubble({ raw }: { raw: string }) {
  const { thinking, response, inThink } = parseThinking(raw);
  return (
    <div className="flex justify-start mb-4">
      <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-sm mr-2 flex-shrink-0 mt-1">
        📚
      </div>
      <div className="max-w-[75%]">
        <ThinkingBlock text={thinking} done={!inThink} />
        {response && (
          <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white border border-gray-200 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
            {response}
            <span className="inline-block w-1.5 h-3 bg-gray-400 animate-pulse ml-0.5 align-middle" />
          </div>
        )}
        {inThink && !response && (
          <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white border border-gray-200 text-sm text-gray-400">
            ···
          </div>
        )}
      </div>
    </div>
  );
}

// 完成後的 AI 訊息氣泡（含可折疊思考過程）
function AssistantBubble({ message }: { message: Message }) {
  const { thinking, response } = parseThinking(message.content);
  if (!thinking) return <ChatBubble message={message} />;
  return (
    <div className="flex justify-start mb-4">
      <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-sm mr-2 flex-shrink-0 mt-1">
        📚
      </div>
      <div className="max-w-[75%]">
        <ThinkingBlock text={thinking} done={true} />
        {response && (
          <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white border border-gray-200 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
            {response}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const navDocumentId: number | undefined = (location.state as { documentId?: number })?.documentId;

  const [session, setSession] = useState<SessionDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const autoSentRef = useRef(false);

  useEffect(() => {
    if (!sessionId) return;
    getSession(Number(sessionId)).then((s) => {
      setSession(s);
      setMessages(s.messages);
      if (s.messages.length === 0 && !autoSentRef.current) {
        autoSentRef.current = true;
        const firstMsg = getInitialMessage(s.direction_key, s.direction_label);
        // 延一個 tick 讓 React 完成渲染後再開始串流
        setTimeout(() => streamFromApi(firstMsg, Number(sessionId), true), 50);
      }
    });
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  async function streamFromApi(text: string, sid: number, isAuto = false) {
    if (!isAuto) {
      setMessages((prev) => [
        ...prev,
        { id: Date.now(), role: "user", content: text, created_at: new Date().toISOString() },
      ]);
    }
    setStreaming(true);
    setStreamingText("");

    let full = "";
    try {
      const resp = await fetch(`/api/sessions/${sid}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ content: text }),
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`);
      }

      for await (const payload of parseSse(resp.body)) {
        if (payload === "[DONE]") break;
        if (payload.startsWith("[ERROR]")) {
          full += payload.slice(7);
          break;
        }
        full += payload.replace(/\\n/g, "\n");
        setStreamingText(full);
      }
    } catch (err) {
      full = `連線錯誤：${err instanceof Error ? err.message : String(err)}`;
      setStreamingText(full);
    }

    const finalContent = full || "（無回應）";
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + 1,
        role: "assistant",
        content: finalContent,
        created_at: new Date().toISOString(),
      },
    ]);
    setStreamingText("");
    setStreaming(false);
    setTimeout(() => inputRef.current?.focus(), 100);
  }

  async function sendMessage() {
    if (!input.trim() || streaming || !sessionId) return;
    const text = input.trim();
    setInput("");
    await streamFromApi(text, Number(sessionId));
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      sendMessage();
    }
  }

  const documentId = navDocumentId ?? session?.document_id;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <AppHeader />
      <div className="flex flex-1 overflow-hidden max-w-5xl mx-auto w-full px-4 py-4 gap-4">
        {/* Sidebar */}
        <div className="w-60 flex-shrink-0">
          <div className="bg-white border border-gray-200 rounded-xl p-4 sticky top-20">
            <button
              onClick={() => documentId && navigate(`/documents/${documentId}`)}
              disabled={!documentId}
              className="text-xs text-gray-400 hover:text-indigo-500 mb-3 flex items-center gap-1 disabled:opacity-30"
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
            {messages.length === 0 && !streaming && !streamingText && (
              <div className="text-center text-gray-400 py-16">
                <div className="text-3xl mb-3">{session?.direction_emoji ?? "💬"}</div>
                <p className="text-sm animate-pulse">載入中...</p>
              </div>
            )}

            {messages.map((msg) =>
              msg.role === "assistant" ? (
                <AssistantBubble key={msg.id} message={msg} />
              ) : (
                <ChatBubble key={msg.id} message={msg} />
              )
            )}

            {/* 串流進行中 */}
            {streaming && (
              streamingText
                ? <StreamingBubble raw={streamingText} />
                : (
                  <div className="flex justify-start mb-4">
                    <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-sm mr-2 flex-shrink-0">📚</div>
                    <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-tl-sm text-gray-400 text-sm flex items-center gap-1">
                      <span className="animate-bounce" style={{ animationDelay: "0ms" }}>·</span>
                      <span className="animate-bounce" style={{ animationDelay: "150ms" }}>·</span>
                      <span className="animate-bounce" style={{ animationDelay: "300ms" }}>·</span>
                    </div>
                  </div>
                )
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
