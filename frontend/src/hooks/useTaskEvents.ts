import { useEffect, useRef, useState } from 'react'
import type { ProgressEventInfo } from '../api/tasks'

type Options = {
  enabled: boolean
  taskId: string | undefined
  onTerminal?: () => void
}

export function useTaskEvents({ enabled, taskId, onTerminal }: Options) {
  const [events, setEvents] = useState<ProgressEventInfo[]>([])
  const [connected, setConnected] = useState(false)
  const seenIds = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (!enabled || !taskId) {
      setConnected(false)
      return
    }
    seenIds.current = new Set()
    setEvents([])
    const source = new EventSource(`/api/tasks/${taskId}/events`, { withCredentials: true })

    source.onopen = () => setConnected(true)
    source.onerror = () => setConnected(false)

    source.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as ProgressEventInfo
        if (data.id && seenIds.current.has(data.id)) return
        if (data.id) seenIds.current.add(data.id)
        setEvents((prev) => [...prev, data])
        if (data.event_type === 'agent_finish' || data.event_type === 'error') {
          onTerminal?.()
        }
      } catch {
        /* ignore malformed messages */
      }
    }

    return () => {
      source.close()
      setConnected(false)
    }
  }, [enabled, taskId, onTerminal])

  return { events, connected }
}
