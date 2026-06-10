import { createContext, useContext } from "react";

export interface User {
  id: number;
  nickname: string;
  role: "student" | "admin";
}

export interface SessionContextValue {
  user: User | null;
  loading: boolean;
  setUser: (u: User | null) => void;
  logout: () => Promise<void>;
}

export const SessionContext = createContext<SessionContextValue | null>(null);

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
