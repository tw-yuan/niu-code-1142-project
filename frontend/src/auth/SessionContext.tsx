import { useEffect, useState, type ReactNode } from "react";
import { getMe, logout as apiLogout } from "../api/auth";
import { SessionContext, type User } from "./useSession";

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function logout() {
    await apiLogout().catch(() => {});
    setUser(null);
  }

  return (
    <SessionContext.Provider value={{ user, loading, setUser, logout }}>
      {children}
    </SessionContext.Provider>
  );
}
