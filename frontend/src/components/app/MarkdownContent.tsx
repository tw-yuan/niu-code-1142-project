import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"

interface Props {
  children: string
  className?: string
}

const markdownComponents: Components = {
  table({ children }) {
    return (
      <div className="my-4 overflow-x-auto rounded-lg border border-zinc-200">
        <table className="my-0 w-full border-collapse text-left text-sm">{children}</table>
      </div>
    )
  },
  th({ children }) {
    return <th className="border-b border-zinc-200 bg-zinc-50 px-3 py-2 font-semibold text-zinc-900">{children}</th>
  },
  td({ children }) {
    return <td className="border-b border-zinc-100 px-3 py-2 align-top text-zinc-700">{children}</td>
  },
  a({ children, href }) {
    return (
      <a href={href} target="_blank" rel="noreferrer">
        {children}
      </a>
    )
  },
}

export function MarkdownContent({ children, className = "" }: Props) {
  return (
    <div className={["prose prose-zinc max-w-none whitespace-normal", className].join(" ")}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {children}
      </ReactMarkdown>
    </div>
  )
}
