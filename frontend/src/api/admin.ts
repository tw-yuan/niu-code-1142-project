import client from "./client";
import type { Message } from "./sessions";

export interface AdminOverview {
  users: number;
  documents: number;
  sessions: number;
  messages: number;
  failed_documents: number;
}

export interface AdminUser {
  id: number;
  nickname: string;
  role: "student" | "admin";
  document_count: number;
  session_count: number;
  created_at: string;
}

export interface AdminDocument {
  id: number;
  user_id: number;
  owner_nickname: string | null;
  original_filename: string;
  file_type: string;
  file_size: number;
  token_count: number;
  parse_status: string;
  index_status: string;
  error_message: string | null;
  created_at: string;
}

export interface AdminSession {
  id: number;
  user_id: number;
  owner_nickname: string | null;
  document_id: number;
  document_original_filename: string | null;
  direction_key: string;
  direction_label: string;
  direction_emoji: string | null;
  message_count: number;
  created_at: string;
}

export interface AdminSessionDetail extends AdminSession {
  messages: Message[];
}

export async function getOverview(): Promise<AdminOverview> {
  const { data } = await client.get("/admin/overview");
  return data;
}

export async function listAdminUsers(): Promise<AdminUser[]> {
  const { data } = await client.get("/admin/users");
  return data;
}

export async function updateAdminUserRole(id: number, role: "student" | "admin"): Promise<AdminUser> {
  const { data } = await client.patch(`/admin/users/${id}`, { role });
  return data;
}

export async function listAdminDocuments(): Promise<AdminDocument[]> {
  const { data } = await client.get("/admin/documents");
  return data;
}

export async function deleteAdminDocument(id: number): Promise<void> {
  await client.delete(`/admin/documents/${id}`);
}

export async function retryAdminDocument(id: number): Promise<AdminDocument> {
  const { data } = await client.post(`/admin/documents/${id}/retry`);
  return data;
}

export async function listAdminSessions(): Promise<AdminSession[]> {
  const { data } = await client.get("/admin/sessions");
  return data;
}

export async function getAdminSession(id: number): Promise<AdminSessionDetail> {
  const { data } = await client.get(`/admin/sessions/${id}`);
  return data;
}

export async function deleteAdminSession(id: number): Promise<void> {
  await client.delete(`/admin/sessions/${id}`);
}
