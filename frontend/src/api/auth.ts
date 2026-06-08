import client from "./client";

export async function login(nickname: string, password: string) {
  const { data } = await client.post("/auth/login", { nickname, password });
  return data as { message: string; nickname: string };
}

export async function logout() {
  await client.post("/auth/logout");
}

export async function getMe() {
  const { data } = await client.get("/auth/me");
  return data as { id: number; nickname: string };
}
