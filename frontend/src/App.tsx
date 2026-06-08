import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { SessionProvider } from "./auth/SessionContext";
import RequireAuth from "./auth/RequireAuth";
import LoginPage from "./pages/LoginPage";
import HomePage from "./pages/HomePage";
import DocumentPage from "./pages/DocumentPage";
import ChatPage from "./pages/ChatPage";
import HistoryPage from "./pages/HistoryPage";

export default function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
          <Route path="/documents/:docId" element={<RequireAuth><DocumentPage /></RequireAuth>} />
          <Route path="/sessions/:sessionId" element={<RequireAuth><ChatPage /></RequireAuth>} />
          <Route path="/history" element={<RequireAuth><HistoryPage /></RequireAuth>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </SessionProvider>
    </BrowserRouter>
  );
}
