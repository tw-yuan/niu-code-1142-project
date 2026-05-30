import AppHeader from '../components/AppHeader'

export default function AdminSettingsPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-bold">系統設定</h1>
        <p className="text-sm text-slate-600 mt-2">M8 會接上實際設定表單。</p>
      </main>
    </div>
  )
}
