import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Eye, EyeOff } from 'lucide-react'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username || !password) { setError('Username and password required'); return }
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-[#0a0b0d] px-4"
      style={{
        background: 'radial-gradient(ellipse at 50% 30%, rgba(59,130,246,0.05) 0%, #0a0b0d 70%)',
      }}
    >
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="font-mono font-bold text-3xl text-[#e8eaf0] tracking-widest mb-1"
            style={{ textShadow: '0 0 30px rgba(59,130,246,0.4)' }}>
            GHOST<span className="text-[#3b82f6]">EXODUS</span>
          </div>
          <div className="text-[0.65rem] font-mono tracking-[0.35em] text-[#4a5568] uppercase">
            OSINT Intelligence Platform
          </div>
        </div>

        {/* Card */}
        <div className="bg-[#111318] border border-[#1f2330] rounded-lg p-8 shadow-2xl">
          <div className="text-[0.65rem] font-mono tracking-[0.2em] text-[#4a5568] uppercase mb-6">
            Analyst Authentication
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1.5 uppercase tracking-wider">
                Username
              </label>
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="analyst_01"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1.5 uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  disabled={loading}
                  style={{ paddingRight: '2.5rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#4a5568] hover:text-[#8892a4]"
                >
                  {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="text-xs font-mono text-[#f87171] bg-[#7f1d1d]/20 border border-[#7f1d1d]/40 px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full mt-2 py-2.5 text-sm uppercase tracking-widest disabled:opacity-50"
            >
              {loading ? 'AUTHENTICATING…' : 'AUTHENTICATE'}
            </button>
          </form>
        </div>

        <div className="text-center mt-6 text-[0.6rem] font-mono text-[#4a5568]">
          CLASSIFICATION: SENSITIVE — AUTHORISED USERS ONLY
        </div>
      </div>
    </div>
  )
}
