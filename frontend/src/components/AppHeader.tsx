import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useSession } from "../auth/useSession";

export default function AppHeader() {
  const { user, logout } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  const links = [
    { to: "/", label: "我的講義", show: true },
    { to: "/history", label: "學習歷史", show: true },
    { to: "/admin", label: "管理後台", show: user?.role === "admin" },
  ];
  const linkClass = (to: string) => {
    const active = to === "/" ? location.pathname === "/" : location.pathname.startsWith(to);
    return active
      ? "rounded-md bg-indigo-50 px-3 py-2 text-indigo-700"
      : "rounded-md px-3 py-2 text-gray-600 hover:bg-gray-50 hover:text-indigo-600";
  };

  const renderNav = () => (
    <>
      {links.filter((item) => item.show).map((item) => (
        <Link key={item.to} to={item.to} className={linkClass(item.to)} onClick={() => setOpen(false)}>
          {item.label}
        </Link>
      ))}
      {user && (
        <div className="flex items-center gap-3 px-3 py-2">
          <span className="text-gray-400">Hi, {user.nickname}</span>
          <button onClick={handleLogout} className="text-gray-500 hover:text-red-500 transition-colors">
            登出
          </button>
        </div>
      )}
    </>
  );

  return (
    <header className="sticky top-0 z-10 border-b border-gray-200 bg-white px-4 py-3 sm:px-6">
      <div className="flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-indigo-600 font-semibold text-lg">
          📚 學業輔助
        </Link>
        <button
          onClick={() => setOpen((v) => !v)}
          className="rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-500 sm:hidden"
        >
          選單
        </button>
        <nav className="hidden items-center gap-1 text-sm sm:flex">{renderNav()}</nav>
      </div>
      {open && <nav className="mt-3 grid gap-1 border-t border-gray-100 pt-3 text-sm sm:hidden">{renderNav()}</nav>}
    </header>
  );
}
