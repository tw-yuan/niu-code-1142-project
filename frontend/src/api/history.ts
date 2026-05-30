import { api } from './client'
import type { TaskStatus } from './tasks'

export type HistoryItem = {
  id: string
  status: TaskStatus
  assignment_text: string
  agent_title: string | null
  iterations_used: number
  created_at: string
  updated_at: string
  owner_display_name: string | null
}

export function listHistory() {
  return api.get<HistoryItem[]>('/api/history')
}

export function deleteTask(taskId: string) {
  return api.delete<void>(`/api/tasks/${taskId}`)
}
