import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { adminLogin } from '../api/auth';
import ErrorAlert from '../components/ErrorAlert';

export default function AdminLoginPage() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setError('');
    setLoading(true);
    try {
      await adminLogin(password);
      navigate('/admin/settings');
    } catch (err: any) {
      setError(err.response?.data?.detail || '登入失敗，請重試');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-200 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-gray-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">管理者登入</h1>
          <p className="text-gray-500 text-sm mt-1">AI 課業輔助系統後台</p>
        </div>

        {error && <ErrorAlert message={error} onClose={() => setError('')} />}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">管理者密碼</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="輸入管理者密碼"
              className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-gray-300 focus:border-gray-400 outline-none"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading || !password}
            className="w-full bg-gray-800 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {loading ? '登入中...' : '登入'}
          </button>
        </form>

        <p className="text-center text-xs text-gray-400 mt-6">
          <a href="/login" className="hover:text-gray-600">返回學生登入</a>
        </p>
      </div>
    </div>
  );
}
