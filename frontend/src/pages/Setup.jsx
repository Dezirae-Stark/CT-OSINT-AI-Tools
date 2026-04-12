import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

export default function Setup() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    if (password !== confirm) { setError('Passwords do not match'); return }
    setError('')
    setLoading(true)
    try {
      await api.post('/api/setup/init', { username, password })
      navigate('/login')
    } catch (err) {
      setError(err.response?.data?.detail || 'Setup failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0b0d] px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-10">
          <div className="font-mono font-bold text-3xl text-[#e8eaf0] tracking-widest mb-1">
            GHOST<span className="text-[#3b82f6]">EXODUS</span>
          </div>
          <div className="text-[0.65rem] font-mono tracking-[0.35em] text-[#4a5568]">
            FIRST-RUN SETUP
          </div>
        </div>

        <div className="bg-[#111318] border border-[#2d3447] rounded-lg p-8">
          <div className="text-xs font-mono text-[#f59e0b] border border-[#78350f]/50 bg-[#78350f]/10 px-3 py-2 mb-6">
            Create the initial administrator account. This page will be locked after setup.
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1.5 uppercase tracking-wider">
                Admin Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1.5 uppercase tracking-wider">
                Password (min. 8 chars)
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1.5 uppercase tracking-wider">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••••"
                required
              />
            </div>
            {error && (
              <div className="text-xs font-mono text-[#f87171] bg-[#7f1d1d]/20 border border-[#7f1d1d]/40 px-3 py-2">
                {error}
              </div>
            )}
            <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 uppercase tracking-widest disabled:opacity-50">
              {loading ? 'CREATING…' : 'CREATE ADMIN ACCOUNT'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
