import { useEffect, useRef, useCallback, useState } from 'react'
import { useAuthStore } from '../store/authStore'

export function useWebSocket(onMessage) {
  const ws = useRef(null)
  const reconnectTimer = useRef(null)
  const reconnectDelay = useRef(1000)
  const [connected, setConnected] = useState(false)
  const token = useAuthStore((s) => s.token)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    if (!token) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${window.location.host}/api/feed/live`

    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      setConnected(true)
      reconnectDelay.current = 1000
    }

    ws.current.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        onMessageRef.current(data)
      } catch {
        // ignore parse errors
      }
    }

    ws.current.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000)
        connect()
      }, reconnectDelay.current)
    }

    ws.current.onerror = () => {
      ws.current?.close()
    }
  }, [token])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  // Send keepalive ping every 20s
  useEffect(() => {
    const interval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 20000)
    return () => clearInterval(interval)
  }, [])

  return { connected }
}
