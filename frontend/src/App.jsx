import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuthStore } from './store/authStore'
import ProtectedRoute from './components/Layout/ProtectedRoute'
import Layout from './components/Layout/Layout'

// Pages
import Login from './pages/Login'
import Setup from './pages/Setup'
import Dashboard from './pages/Dashboard'
import Search from './pages/Search'
import EntityMap from './pages/EntityMap'
import Timeline from './pages/Timeline'
import AlertRules from './pages/AlertRules'
import Reports from './pages/Reports'
import Evidence from './pages/Evidence'
import Settings from './pages/Settings'

export default function App() {
  const token = useAuthStore((s) => s.token)
  const [setupRequired, setSetupRequired] = useState(null)

  useEffect(() => {
    fetch('/api/setup/status')
      .then((r) => r.json())
      .then((data) => setSetupRequired(data.setup_required))
      .catch(() => setSetupRequired(false))
  }, [])

  if (setupRequired === null) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0a0b0d]">
        <span className="text-[#3b82f6] font-mono text-sm animate-pulse">INITIALIZING…</span>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Setup wizard — only accessible if no users exist */}
        <Route path="/setup" element={setupRequired ? <Setup /> : <Navigate to="/" replace />} />

        {/* Auth */}
        <Route path="/login" element={!token ? <Login /> : <Navigate to="/" replace />} />

        {/* App — all require auth */}
        <Route
          path="/"
          element={
            setupRequired
              ? <Navigate to="/setup" replace />
              : <ProtectedRoute><Layout /></ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="search" element={<Search />} />
          <Route path="entities" element={<EntityMap />} />
          <Route path="timeline" element={<Timeline />} />
          <Route path="alerts" element={<AlertRules />} />
          <Route path="reports" element={<Reports />} />
          <Route path="evidence" element={<Evidence />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
