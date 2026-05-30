import { useCallback, useRef, useState, type DragEvent, type ClipboardEvent } from 'react'
import { formatBytes } from '../utils/format'

type Props = {
  title: string
  subtitle?: string
  files: File[]
  onChange: (files: File[]) => void
  maxSizeMB?: number
  acceptHint?: string
}

export default function FilePickerCard({
  title,
  subtitle,
  files,
  onChange,
  maxSizeMB = 10,
  acceptHint,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      const incomingArr = Array.from(incoming)
      const maxBytes = maxSizeMB * 1024 * 1024
      const overSize = incomingArr.filter((f) => f.size > maxBytes)
      const ok = incomingArr.filter((f) => f.size <= maxBytes)
      if (overSize.length > 0) {
        setError(`超過 ${maxSizeMB}MB 上限：${overSize.map((f) => f.name).join(', ')}`)
      } else {
        setError(null)
      }
      const merged = [...files]
      for (const f of ok) {
        if (!merged.some((m) => m.name === f.name && m.size === f.size)) merged.push(f)
      }
      onChange(merged)
    },
    [files, onChange, maxSizeMB],
  )

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files)
  }

  function onPaste(e: ClipboardEvent<HTMLDivElement>) {
    const items = e.clipboardData?.items
    if (!items) return
    const out: File[] = []
    for (let i = 0; i < items.length; i += 1) {
      const it = items[i]
      if (it.kind === 'file') {
        const f = it.getAsFile()
        if (f) out.push(f)
      }
    }
    if (out.length) {
      e.preventDefault()
      addFiles(out)
    }
  }

  function removeAt(i: number) {
    const next = files.slice()
    next.splice(i, 1)
    onChange(next)
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
      <header>
        <h2 className="font-semibold text-slate-900">{title}</h2>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </header>

      <div
        tabIndex={0}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onPaste={onPaste}
        onClick={() => inputRef.current?.click()}
        className={`rounded-xl border-2 border-dashed p-6 text-center cursor-pointer transition-colors ${
          dragOver
            ? 'border-blue-400 bg-blue-50'
            : 'border-slate-300 hover:border-slate-400 bg-slate-50'
        }`}
      >
        <p className="text-sm text-slate-700">點此選檔、拖放或 Ctrl+V 貼上</p>
        <p className="text-xs text-slate-500 mt-1">{acceptHint ?? `每檔最多 ${maxSizeMB}MB，不限格式`}</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) addFiles(e.target.files)
            e.target.value = ''
          }}
        />
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>
      )}

      {files.length > 0 && (
        <ul className="divide-y divide-slate-100 border border-slate-200 rounded-lg">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex items-center justify-between px-3 py-2 text-sm">
              <div className="flex-1 min-w-0">
                <div className="truncate text-slate-800">{f.name}</div>
                <div className="text-xs text-slate-500">{formatBytes(f.size)}</div>
              </div>
              <button
                type="button"
                onClick={() => removeAt(i)}
                className="ml-3 text-xs text-slate-500 hover:text-red-600"
              >
                移除
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
