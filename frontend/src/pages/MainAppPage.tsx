import AppHeader from '../components/AppHeader'
import { useSession } from '../auth/SessionContext'

export default function MainAppPage() {
  const { session } = useSession()
  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-bold">主系統</h1>
        <p className="text-sm text-slate-600 mt-2">
          歡迎，{session?.display_name ?? '學生'}。M3 後會出現左右分欄上傳介面。
        </p>
      </main>
    </div>
  )
}
