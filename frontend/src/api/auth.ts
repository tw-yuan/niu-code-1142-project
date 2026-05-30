import { api } from './client'

export type SessionInfo = {
  role: 'student' | 'admin'
  display_name: string | null
  user_id: string | null
}

export function studentLogin(nickname: string, password: string) {
  return api.post<SessionInfo>('/api/auth/student/login', { nickname, password })
}

export function adminLogin(password: string) {
  return api.post<SessionInfo>('/api/auth/admin/login', { password })
}

export function fetchMe() {
  return api.get<SessionInfo | null>('/api/auth/me')
}

export function logout() {
  return api.post<void>('/api/auth/logout')
}
