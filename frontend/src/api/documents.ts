import client from "./client";

export interface Document {
  id: number;
  original_filename: string;
  file_type: string;
  file_size: number;
  token_count: number;
  index_status: string;
  created_at: string;
}

export interface Direction {
  key: string;
  label: string;
  description: string;
  emoji: string;
  is_dynamic: boolean;
}

export async function uploadDocument(file: File): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
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

export async function getDirections(id: number, refresh = false): Promise<{ directions: Direction[]; cached: boolean }> {
  const { data } = await client.get(`/documents/${id}/directions`, {
    params: refresh ? { refresh: true } : undefined,
  });
  return data;
}
