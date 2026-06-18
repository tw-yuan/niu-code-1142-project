import ReactMarkdown, { type Components } from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";

interface Props {
  children: string;
  className?: string;
}

const inlineComponents: Components = {
  p({ children }) {
    return <>{children}</>;
  },
};

export function MathText({ children, className = "" }: Props) {
  const normalized = normalizeMathDelimiters(children);
  return (
    <span className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={inlineComponents}
      >
        {normalized}
      </ReactMarkdown>
    </span>
  );
}

function normalizeMathDelimiters(value: string) {
  return value
    .replace(/\\\$/g, "$")
    .replace(/\\\((.+?)\\\)/gs, (_match, formula: string) => `$${formula}$`)
    .replace(/\\\[(.+?)\\\]/gs, (_match, formula: string) => `$$${formula}$$`);
}
