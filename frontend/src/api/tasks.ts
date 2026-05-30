import { api } from './client'

export type FileCategory = 'course_material' | 'assignment_file'

export type FileInfo = {
  id: string
  file_category: FileCategory
  original_filename: string
  file_type: string
  file_size: number
  parse_status: 'pending' | 'success' | 'failed' | 'skipped'
  summary: string | null
  error_message: string | null
  created_at: string
}

export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed'

export type TaskInfo = {
  id: string
  status: TaskStatus
  assignment_text: string
  agent_title: string | null
  agent_assignment_summary: string | null
  agent_explanation: string | null
  iterations_used: number
  model_name: string | null
  error_message: string | null
  created_at: string
  updated_at: string
  files: FileInfo[]
}

export type TaskListItem = {
  id: string
  status: TaskStatus
  assignment_text: string
  agent_title: string | null
  iterations_used: number
  created_at: string
  updated_at: string
}

export function createTask(assignment_text: string) {
  return api.post<TaskInfo>('/api/tasks', { assignment_text })
}

export function getTask(taskId: string) {
  return api.get<TaskInfo>(`/api/tasks/${taskId}`)
}

export function listTasks() {
  return api.get<TaskListItem[]>('/api/tasks')
}

export async function uploadFiles(
  taskId: string,
  files: File[],
  category: FileCategory,
): Promise<FileInfo[]> {
  if (files.length === 0) return []
  const form = new FormData()
  form.append('category', category)
  for (const f of files) {
    form.append('files', f, f.name)
  }
  const res = await fetch(`/api/tasks/${taskId}/files`, {
    method: 'POST',
    body: form,
    credentials: 'include',
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const j = await res.json()
      detail = j?.detail ?? detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return (await res.json()) as FileInfo[]
}
