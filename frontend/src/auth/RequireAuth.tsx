import { Navigate } from "react-router-dom";
import { useSession } from "./SessionContext";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useSession();
  if (loading) return <div className="flex items-center justify-center h-screen text-gray-400">載入中...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
