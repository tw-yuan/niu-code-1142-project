import api from './client';

export async function getSettings() {
  const res = await api.get('/admin/settings');
  return res.data;
}

export async function updateSettings(settings: Record<string, string>) {
  const res = await api.put('/admin/settings', { settings });
  return res.data;
}

export async function testApi() {
  const res = await api.post('/admin/test-api');
  return res.data;
}

export async function getSettingsHistory() {
  const res = await api.get('/admin/settings/history');
  return res.data;
}
