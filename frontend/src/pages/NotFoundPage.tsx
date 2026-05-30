import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-4 p-6">
      <h1 className="text-2xl font-bold">404</h1>
      <p className="text-slate-600">找不到頁面</p>
      <Link className="text-blue-600 underline" to="/">
        回首頁
      </Link>
    </main>
  )
}
