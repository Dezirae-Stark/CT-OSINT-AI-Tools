import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import { useWebSocket } from '../../hooks/useWebSocket'
import Toast from '../shared/Toast'

export const FeedContext = React.createContext(null)

export default function Layout() {
  const [wsConnected, setWsConnected] = useState(false)
  const [liveMessages, setLiveMessages] = useState([])
  const [toasts, setToasts] = useState([])

  const addToast = (msg, type = 'info') => {
    const id = Date.now()
    setToasts((prev) => [...prev.slice(-4), { id, msg, type }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000)
  }

  const { connected } = useWebSocket((event) => {
    setWsConnected(true)
    if (event.type === 'new_message') {
      setLiveMessages((prev) => [event.data, ...prev.slice(0, 99)])
      if (['HIGH', 'CRITICAL'].includes(event.data?.severity)) {
        addToast(`${event.data.severity} alert: ${event.data.channel_name}`, 'alert')
      }
    } else if (event.type === 'alert_triggered') {
      addToast(`Alert: ${event.data.rule_name} — ${event.data.severity}`, 'alert')
    }
  })

  React.useEffect(() => {
    setWsConnected(connected)
  }, [connected])

  return (
    <FeedContext.Provider value={{ liveMessages, addToast }}>
      <div className="flex h-screen bg-[#0a0b0d] overflow-hidden">
        <Sidebar />
        <div className="flex-1 ml-60 flex flex-col overflow-hidden">
          <Topbar wsConnected={wsConnected} />
          <main className="flex-1 overflow-y-auto mt-12 p-6">
            <Outlet />
          </main>
        </div>
        {/* Toast notifications */}
        <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50">
          {toasts.map((t) => (
            <Toast key={t.id} message={t.msg} type={t.type} />
          ))}
        </div>
      </div>
    </FeedContext.Provider>
  )
}

import React from 'react'
