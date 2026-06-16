import { create } from "zustand"
import { apiFetch, AuthResponse, User } from "../lib/api"
import { wsManager } from "../lib/ws"

interface AuthState {
  user: User | null
  loading: boolean
  setUser: (user: User | null) => void
  loadMe: () => Promise<void>
  login: (identifier: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  setUser: (user) => set({ user }),
  loadMe: async () => {
    if (!localStorage.getItem("access_token")) {
      set({ user: null, loading: false })
      return
    }
    try {
      const user = await apiFetch<User>("/auth/me")
      set({ user, loading: false })
    } catch {
      set({ user: null, loading: false })
    }
  },
  login: async (identifier, password) => {
    const data = await apiFetch<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    })
    localStorage.setItem("access_token", data.access_token)
    set({ user: data.user })
  },
  register: async (username, email, password) => {
    const data = await apiFetch<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    })
    localStorage.setItem("access_token", data.access_token)
    set({ user: data.user })
  },
  logout: async () => {
    await apiFetch("/auth/logout", { method: "POST" }).catch(() => undefined)
    localStorage.removeItem("access_token")
    wsManager.disconnect()
    set({ user: null })
  },
}))
