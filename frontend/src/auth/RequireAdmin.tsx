import { Navigate } from "react-router-dom";
import { useSession } from "./useSession";

export default function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, loading } = useSession();
  if (loading) return <div className="flex h-screen items-center justify-center text-gray-400">載入中...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}
