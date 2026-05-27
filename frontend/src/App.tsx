import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import StudentLoginPage from './pages/StudentLoginPage';
import AdminLoginPage from './pages/AdminLoginPage';
import MainAppPage from './pages/MainAppPage';
import HistoryPage from './pages/HistoryPage';
import AdminSettingsPage from './pages/AdminSettingsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<StudentLoginPage />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/app" element={<MainAppPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/admin/settings" element={<AdminSettingsPage />} />
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
