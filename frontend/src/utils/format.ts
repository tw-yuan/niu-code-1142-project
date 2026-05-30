export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

export function formatRelative(iso: string): string {
  const then = new Date(iso).getTime()
  const now = Date.now()
  const diffSec = Math.round((now - then) / 1000)
  if (Number.isNaN(diffSec)) return iso
  if (diffSec < 60) return `${diffSec} 秒前`
  if (diffSec < 3600) return `${Math.round(diffSec / 60)} 分鐘前`
  if (diffSec < 86400) return `${Math.round(diffSec / 3600)} 小時前`
  return new Date(iso).toLocaleString('zh-TW')
}

export function parseStatusLabel(status: string): string {
  switch (status) {
    case 'success': return '已解析'
    case 'failed': return '解析失敗'
    case 'skipped': return '未支援格式'
    case 'pending': return '解析中'
    default: return status
  }
}
