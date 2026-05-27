import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Save, Wifi, WifiOff, LogOut, History } from 'lucide-react';
import { getMe, logout } from '../api/auth';
import { getSettings, updateSettings, testApi, getSettingsHistory } from '../api/admin';
import ErrorAlert from '../components/ErrorAlert';
import LoadingIndicator from '../components/LoadingIndicator';
import type { SettingItem, SettingHistoryItem } from '../types/settings';

export default function AdminSettingsPage() {
  const navigate = useNavigate();
  const [settings, setSettings] = useState<SettingItem[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [historyItems, setHistoryItems] = useState<SettingHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    getMe().then((u) => {
      if (u.role !== 'admin') navigate('/login');
    }).catch(() => navigate('/admin/login'));
    loadSettings();
  }, [navigate]);

  const loadSettings = async () => {
    try {
      const data = await getSettings();
      setSettings(data);
      const vals: Record<string, string> = {};
      data.forEach((s: SettingItem) => { vals[s.key] = s.value; });
      setValues(vals);
    } catch {}
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await updateSettings(values);
      setSuccess('設定已儲存');
      loadSettings();
    } catch (err: any) {
      setError(err.response?.data?.detail || '儲存失敗');
    }
    setSaving(false);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testApi();
      setTestResult(result);
    } catch (err: any) {
      setTestResult({ success: false, message: '連線測試失敗' });
    }
    setTesting(false);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/admin/login');
  };

  const loadHistory = async () => {
    try {
      const data = await getSettingsHistory();
      setHistoryItems(data);
      setShowHistory(true);
    } catch {}
  };

  if (loading) return <LoadingIndicator />;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-800">系統管理後台</h1>
          <div className="flex items-center gap-2">
            <button onClick={loadHistory} className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
              <History className="w-4 h-4" /> 變更紀錄
            </button>
            <button onClick={handleLogout} className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50">
              <LogOut className="w-4 h-4" /> 登出
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {error && <div className="mb-4"><ErrorAlert message={error} onClose={() => setError('')} /></div>}
        {success && (
          <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-700">
            {success}
          </div>
        )}

        <div className="bg-white border rounded-lg p-6 space-y-6">
          <h2 className="text-lg font-semibold text-gray-800">API 與系統設定</h2>

          {settings.map((s) => (
            <div key={s.key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{s.label}</label>
              {s.key === 'system_prompt' ? (
                <textarea
                  value={values[s.key] || ''}
                  onChange={(e) => setValues({ ...values, [s.key]: e.target.value })}
                  rows={6}
                  className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-300 focus:border-blue-400 outline-none font-mono"
                />
              ) : (
                <input
                  type={s.is_secret ? 'password' : 'text'}
                  value={values[s.key] || ''}
                  onChange={(e) => setValues({ ...values, [s.key]: e.target.value })}
                  placeholder={s.is_secret ? '輸入新值以更新（留空不修改）' : ''}
                  className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-300 focus:border-blue-400 outline-none"
                />
              )}
              {s.is_secret && <p className="text-xs text-gray-400 mt-1">目前值已遮罩顯示，輸入新值以更新</p>}
            </div>
          ))}

          <div className="flex items-center gap-3 pt-4 border-t">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {saving ? '儲存中...' : '儲存設定'}
            </button>
            <button
              onClick={handleTest}
              disabled={testing}
              className="flex items-center gap-2 px-6 py-2.5 border rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
            >
              {testing ? <Wifi className="w-4 h-4 animate-pulse" /> : <Wifi className="w-4 h-4" />}
              {testing ? '測試中...' : '測試 API 連線'}
            </button>
          </div>

          {testResult && (
            <div className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
              testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}>
              {testResult.success ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
              {testResult.message}
            </div>
          )}
        </div>

        {/* Setting History */}
        {showHistory && (
          <div className="mt-6 bg-white border rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-800">設定變更紀錄</h2>
              <button onClick={() => setShowHistory(false)} className="text-sm text-gray-500 hover:text-gray-700">關閉</button>
            </div>
            {historyItems.length === 0 ? (
              <p className="text-sm text-gray-500">尚無變更紀錄</p>
            ) : (
              <div className="space-y-3">
                {historyItems.map((h) => (
                  <div key={h.id} className="text-sm border-l-2 border-gray-200 pl-3">
                    <p className="font-medium text-gray-700">{h.key}</p>
                    <p className="text-gray-500 text-xs">
                      {h.old_value || '(空)'} → {h.new_value || '(空)'}
                    </p>
                    <p className="text-gray-400 text-xs">
                      {new Date(h.updated_at).toLocaleString('zh-TW')}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
