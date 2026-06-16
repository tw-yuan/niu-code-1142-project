const configured = import.meta.env.VITE_WS_URL ?? "/ws"

function wsUrl(path: string) {
  if (configured.startsWith("ws")) {
    const base = configured.endsWith("/ws") ? configured : `${configured.replace(/\/$/, "")}/ws`
    return `${base}${path}`
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  return `${protocol}//${window.location.host}${configured}${path}`
}

class WSManager {
  private ws: WebSocket | null = null
  private token: string | null = null
  private handlers = new Map<string, Set<(data: any) => void>>()

  connect(token: string) {
    if (
      this.ws &&
      this.token === token &&
      (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return
    }
    this.disconnect()
    this.token = token
    this.ws = new WebSocket(wsUrl(`?token=${encodeURIComponent(token)}`))
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      this.handlers.get(msg.type)?.forEach((fn) => fn(msg))
    }
    this.ws.onclose = () => {
      this.ws = null
      this.token = null
      window.setTimeout(() => {
        const latest = localStorage.getItem("access_token")
        if (latest) this.connect(latest)
      }, 3000)
    }
  }

  disconnect() {
    const current = this.ws
    this.ws = null
    this.token = null
    if (current && current.readyState !== WebSocket.CLOSED) {
      current.close()
    }
  }

  on(type: string, handler: (data: any) => void) {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set())
    this.handlers.get(type)!.add(handler)
    return () => this.handlers.get(type)?.delete(handler)
  }
}

export const wsManager = new WSManager()
