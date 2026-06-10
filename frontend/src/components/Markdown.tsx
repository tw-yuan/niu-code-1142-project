import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
}

// AI 回覆的 Markdown 渲染（標題、清單、表格、程式碼區塊等）
export default function Markdown({ content }: Props) {
  return (
    <div className="space-y-2 [&>*:first-child]:mt-0">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h2 className="mt-3 text-lg font-semibold">{children}</h2>,
          h2: ({ children }) => <h3 className="mt-3 text-base font-semibold">{children}</h3>,
          h3: ({ children }) => <h4 className="mt-3 font-semibold">{children}</h4>,
          h4: ({ children }) => <h5 className="mt-2 font-semibold">{children}</h5>,
          p: ({ children }) => <p className="leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-indigo-600 underline hover:text-indigo-800">
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-indigo-200 pl-3 text-gray-500">{children}</blockquote>
          ),
          code: ({ className, children }) => {
            const isBlock = /language-/.test(className ?? "") || String(children).includes("\n");
            if (isBlock) {
              return (
                <code className="block overflow-x-auto rounded-lg bg-gray-800 text-gray-100 p-3 text-xs leading-relaxed">
                  {children}
                </code>
              );
            }
            return <code className="rounded bg-gray-100 px-1 py-0.5 text-[0.85em] text-pink-600">{children}</code>;
          },
          pre: ({ children }) => <pre className="my-1">{children}</pre>,
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-gray-200 bg-gray-50 px-2 py-1.5 text-left font-semibold">{children}</th>
          ),
          td: ({ children }) => <td className="border border-gray-200 px-2 py-1.5 align-top">{children}</td>,
          hr: () => <hr className="my-3 border-gray-200" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
