import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import type { SessionInfo } from '../api/auth'
import { fetchMe, logout as logoutApi } from '../api/auth'

type SessionState = {
  loading: boolean
  session: SessionInfo | null
  refresh: () => Promise<void>
  setSession: (s: SessionInfo | null) => void
  doLogout: () => Promise<void>
}

const SessionContext = createContext<SessionState | undefined>(undefined)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true)
  const [session, setSession] = useState<SessionInfo | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchMe()
      setSession(data ?? null)
    } catch {
      setSession(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const doLogout = useCallback(async () => {
    try {
      await logoutApi()
    } finally {
      setSession(null)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <SessionContext.Provider value={{ loading, session, refresh, setSession, doLogout }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSession() {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used within SessionProvider')
  return ctx
}
