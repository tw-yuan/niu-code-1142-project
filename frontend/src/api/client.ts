export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail)
  }
}

type FetchOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
}

async function request<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = opts
  const init: RequestInit = {
    method,
    credentials: 'include',
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
  }
  if (body !== undefined) {
    init.body = JSON.stringify(body)
  }

  const res = await fetch(path, init)
  const contentType = res.headers.get('content-type') ?? ''
  const isJson = contentType.includes('application/json')

  if (res.status === 204) {
    return undefined as T
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    if (isJson) {
      try {
        const data = await res.json()
        detail = data?.detail ?? detail
      } catch {
        /* ignore */
      }
    }
    throw new ApiError(res.status, detail)
  }

  if (isJson) {
    return (await res.json()) as T
  }
  return undefined as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
