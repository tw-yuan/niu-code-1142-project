import client from "./client";

export interface Document {
  id: number;
  original_filename: string;
  file_type: string;
  file_size: number;
  course_name?: string | null;
  lesson_topic?: string | null;
  learning_goals?: string | null;
  parsed_preview?: string | null;
  token_count: number;
  parse_status: "uploaded" | "parsing" | "ready" | "failed";
  index_status: string;
  error_message?: string | null;
  created_at: string;
}

export interface Direction {
  key: string;
  label: string;
  description: string;
  emoji: string;
  is_dynamic: boolean;
}

export async function uploadDocument(
  file: File,
  onProgress?: (progress: number) => void,
  metadata?: {
    course_name?: string;
    lesson_topic?: string;
    learning_goals?: string;
  },
): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  if (metadata?.course_name) form.append("course_name", metadata.course_name);
  if (metadata?.lesson_topic) form.append("lesson_topic", metadata.lesson_topic);
  if (metadata?.learning_goals) form.append("learning_goals", metadata.learning_goals);
  const { data } = await client.post("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) return;
      onProgress(Math.round((event.loaded / event.total) * 100));
    },
  });
  return data;
}

export async function listDocuments(): Promise<Document[]> {
  const { data } = await client.get("/documents");
  return data;
}

export async function getDocument(id: number): Promise<Document> {
  const { data } = await client.get(`/documents/${id}`);
  return data;
}

export async function deleteDocument(id: number): Promise<void> {
  await client.delete(`/documents/${id}`);
}

export async function retryDocument(id: number): Promise<Document> {
  const { data } = await client.post(`/documents/${id}/retry`);
  return data;
}

export async function getDirections(id: number, refresh = false): Promise<{ directions: Direction[]; cached: boolean }> {
  const { data } = await client.get(`/documents/${id}/directions`, {
    params: refresh ? { refresh: true } : undefined,
  });
  return data;
}
