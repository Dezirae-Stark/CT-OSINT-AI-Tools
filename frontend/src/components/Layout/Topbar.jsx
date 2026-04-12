import { useLocation } from 'react-router-dom'
import { Wifi, WifiOff } from 'lucide-react'

const PAGE_TITLES = {
  '/':         'Dashboard',
  '/search':   'Semantic Search',
  '/entities': 'Entity Correlation Map',
  '/timeline': 'Activity Timeline',
  '/alerts':   'Alert Rules',
  '/reports':  'Intelligence Reports',
  '/evidence': 'Evidence Archive',
  '/settings': 'System Settings',
}

export default function Topbar({ wsConnected }) {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] || 'GhostExodus'

  return (
    <header className="fixed top-0 left-60 right-0 h-12 bg-[#111318] border-b border-[#1f2330] flex items-center justify-between px-6 z-30">
      <h1 className="font-mono text-sm font-semibold text-[#e8eaf0] tracking-wide">
        {title}
      </h1>
      <div className="flex items-center gap-3">
        {/* Live feed status */}
        <div className={`flex items-center gap-1.5 text-xs font-mono ${wsConnected ? 'text-[#22c55e]' : 'text-[#8892a4]'}`}>
          {wsConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
          <span>{wsConnected ? 'LIVE' : 'OFFLINE'}</span>
        </div>
        {/* UTC clock */}
        <UTCClock />
      </div>
    </header>
  )
}

function UTCClock() {
  const [time, setTime] = React.useState(new Date().toISOString().slice(11, 19))

  React.useEffect(() => {
    const t = setInterval(() => {
      setTime(new Date().toISOString().slice(11, 19))
    }, 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <span className="font-mono text-xs text-[#4a5568]">
      {time} UTC
    </span>
  )
}

import React from 'react'
