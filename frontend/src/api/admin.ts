import { api } from './client'

export type AdminSettingsView = {
  system_prompt: string
  model_name: string
  base_url: string
  temperature: number
  max_output_tokens: number
  max_iterations: number
  max_file_size_mb: number
  max_files_per_task: number
  disabled_tools: string[]
  available_tools: string[]
  api_key_configured: boolean
  api_key_preview: string | null
  default_system_prompt: string
}

export type AdminSettingsUpdate = Partial<{
  system_prompt: string
  model_name: string
  base_url: string
  temperature: number
  max_output_tokens: number
  max_iterations: number
  max_file_size_mb: number
  max_files_per_task: number
  disabled_tools: string[]
}>

export type TestApiResult = {
  ok: boolean
  latency_ms: number | null
  model: string
  base_url: string
  tool_calling_supported: boolean | null
  detail: string | null
}

export function getAdminSettings() {
  return api.get<AdminSettingsView>('/api/admin/settings')
}

export function updateAdminSettings(body: AdminSettingsUpdate) {
  return api.put<AdminSettingsView>('/api/admin/settings', body)
}

export function testApi(body: { base_url?: string; model_name?: string }) {
  return api.post<TestApiResult>('/api/admin/test-api', body)
}
