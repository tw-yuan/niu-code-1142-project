import { useEffect, useState } from "react"
import { Citation } from "../../lib/api"
import { StreamEvent } from "../../lib/stream"

interface Props {
  stream: AsyncGenerator<StreamEvent>
  onCitations?: (citations: Citation[]) => void
  onComplete?: (fullText: string) => void
}

export function StreamingText({ stream, onCitations, onComplete }: Props) {
  const [content, setContent] = useState("")
  const [isStreaming, setIsStreaming] = useState(true)

  useEffect(() => {
    let full = ""
    let active = true
    ;(async () => {
      for await (const event of stream) {
        if (!active) return
        if (event.type === "chunk") {
          full += event.content
          setContent(full)
        } else if (event.type === "citations") {
          onCitations?.(event.data)
        } else if (event.type === "error") {
          setContent((prev) => `${prev}\n\n[錯誤：${event.message}]`)
        }
      }
      setIsStreaming(false)
      onComplete?.(full)
    })()
    return () => {
      active = false
    }
  }, [stream, onCitations, onComplete])

  return (
    <div className="prose prose-zinc max-w-none whitespace-pre-wrap text-sm leading-7">
      {content}
      {isStreaming && <span className="animate-pulse">|</span>}
    </div>
  )
}

