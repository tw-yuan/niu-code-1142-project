import { Link, useNavigate } from "react-router-dom";
import { useSession } from "../auth/SessionContext";

export default function AppHeader() {
  const { user, logout } = useSession();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
      <Link to="/" className="flex items-center gap-2 text-indigo-600 font-semibold text-lg">
        📚 學業輔助
      </Link>
      <nav className="flex items-center gap-4 text-sm">
        <Link to="/" className="text-gray-600 hover:text-indigo-600">我的講義</Link>
        <Link to="/history" className="text-gray-600 hover:text-indigo-600">學習歷史</Link>
        {user && (
          <div className="flex items-center gap-3">
            <span className="text-gray-400">Hi, {user.nickname}</span>
            <button
              onClick={handleLogout}
              className="text-gray-500 hover:text-red-500 transition-colors"
            >
              登出
            </button>
          </div>
        )}
      </nav>
    </header>
  );
}
