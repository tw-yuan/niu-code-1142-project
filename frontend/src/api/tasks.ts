import api from './client';

export async function createTask(assignmentText: string, outputFormats: string[]) {
  const res = await api.post('/tasks', { assignment_text: assignmentText, output_formats: outputFormats });
  return res.data;
}

export async function uploadFile(taskId: string, file: File, category: string) {
  const form = new FormData();
  form.append('file', file);
  form.append('file_category', category);
  const res = await api.post(`/tasks/${taskId}/files`, form);
  return res.data;
}

export async function getTask(taskId: string) {
  const res = await api.get(`/tasks/${taskId}`);
  return res.data;
}

export async function deleteTask(taskId: string) {
  const res = await api.delete(`/tasks/${taskId}`);
  return res.data;
}

export async function getHistory() {
  const res = await api.get('/history');
  return res.data;
}

export function getDownloadUrl(taskId: string, fileId: string) {
  return `/api/tasks/${taskId}/download/${fileId}`;
}

export function createEventSource(taskId: string): EventSource {
  return new EventSource(`/api/tasks/${taskId}/events`);
}
