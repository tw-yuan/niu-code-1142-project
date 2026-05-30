import AppHeader from '../components/AppHeader'

export default function HistoryPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-bold">歷史紀錄</h1>
        <p className="text-sm text-slate-600 mt-2">M7 會接上實際紀錄。</p>
      </main>
    </div>
  )
}
