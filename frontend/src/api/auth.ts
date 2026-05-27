import api from './client';

export async function studentLogin(displayName: string, password: string) {
  const res = await api.post('/auth/student/login', { display_name: displayName, password });
  return res.data;
}

export async function adminLogin(password: string) {
  const res = await api.post('/auth/admin/login', { password });
  return res.data;
}

export async function logout() {
  const res = await api.post('/auth/logout');
  return res.data;
}

export async function getMe() {
  const res = await api.get('/auth/me');
  return res.data;
}
