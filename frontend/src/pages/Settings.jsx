import { useEffect, useState } from 'react'
import { Plus, Trash2, RefreshCw } from 'lucide-react'
import api from '../api/client'
import Spinner from '../components/shared/Spinner'
import Modal from '../components/shared/Modal'
import { useAuth } from '../hooks/useAuth'

function Tab({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs font-mono px-4 py-2 border-b-2 transition-all uppercase tracking-wider
        ${active ? 'border-[#3b82f6] text-[#3b82f6]' : 'border-transparent text-[#4a5568] hover:text-[#8892a4]'}`}
    >
      {label}
    </button>
  )
}

function ChannelsTab() {
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [identifier, setIdentifier] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [adding, setAdding] = useState(false)
  const [scraping, setScraping] = useState(null)
  const { isAnalyst, isAdmin } = useAuth()

  const load = () => {
    api.get('/api/channels').then((r) => setChannels(r.data || [])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const handleAdd = async (e) => {
    e.preventDefault()
    setAdding(true)
    try {
      await api.post('/api/channels', { identifier, display_name: displayName })
      setShowAdd(false)
      setIdentifier('')
      setDisplayName('')
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add channel')
    } finally {
      setAdding(false)
    }
  }

  const handleRemove = async (id) => {
    if (!confirm('Remove this channel from monitoring?')) return
    await api.delete(`/api/channels/${id}`).catch(console.error)
    load()
  }

  const handleRescrape = async (id) => {
    setScraping(id)
    try {
      await api.post(`/api/channels/${id}/rescrape`)
    } finally {
      setScraping(null)
    }
  }

  if (loading) return <Spinner label="Loading channels…" />

  return (
    <div>
      {isAnalyst && (
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2 py-1.5 px-4 mb-4 text-xs">
          <Plus size={12} /> ADD CHANNEL
        </button>
      )}
      {channels.length === 0
        ? <div className="text-center py-10 text-[#4a5568] font-mono text-sm">NO CHANNELS MONITORED</div>
        : (
          <table>
            <thead><tr><th>Display Name</th><th>Username</th><th>Status</th><th>Last Checked</th><th>Messages</th><th>Actions</th></tr></thead>
            <tbody>
              {channels.map((ch) => (
                <tr key={ch.id}>
                  <td className="font-mono text-xs text-[#e8eaf0]">{ch.display_name}</td>
                  <td className="font-mono text-xs text-[#3b82f6]">{ch.username ? `@${ch.username}` : '—'}</td>
                  <td>
                    <span className={`text-xs font-mono ${ch.is_active ? 'text-[#22c55e]' : 'text-[#4a5568]'}`}>
                      {ch.is_active ? '● ACTIVE' : '○ INACTIVE'}
                    </span>
                  </td>
                  <td className="font-mono text-xs text-[#4a5568]">{ch.last_checked?.slice(0, 16).replace('T', ' ') || '—'}</td>
                  <td className="font-mono text-xs text-[#8892a4]">{ch.message_count}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      {isAnalyst && (
                        <button
                          onClick={() => handleRescrape(ch.id)}
                          disabled={scraping === ch.id}
                          title="Re-scrape history"
                          className="text-[#4a5568] hover:text-[#3b82f6] disabled:opacity-40"
                        >
                          {scraping === ch.id ? <Spinner size={12} /> : <RefreshCw size={12} />}
                        </button>
                      )}
                      {isAdmin && (
                        <button onClick={() => handleRemove(ch.id)} className="text-[#4a5568] hover:text-[#f87171]">
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      }
      {showAdd && (
        <Modal title="Add Monitored Channel" onClose={() => setShowAdd(false)}>
          <form onSubmit={handleAdd} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">
                Telegram Username or URL
              </label>
              <input
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="@channelname or t.me/channelname"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">Display Name</label>
              <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Optional display name" />
            </div>
            <div className="flex gap-2 pt-2">
              <button type="submit" disabled={adding} className="btn-primary py-1.5 px-5 disabled:opacity-50">
                {adding ? 'ADDING…' : 'ADD CHANNEL'}
              </button>
              <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary py-1.5 px-5">CANCEL</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

function UsersTab() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('VIEWER')

  const load = () => {
    api.get('/api/admin/users').then((r) => setUsers(r.data || [])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    await api.post('/api/admin/users', { username, password, role }).catch((err) => {
      alert(err.response?.data?.detail || 'Failed')
    })
    setShowAdd(false)
    setUsername(''); setPassword(''); setRole('VIEWER')
    load()
  }

  if (loading) return <Spinner label="Loading users…" />

  return (
    <div>
      <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2 py-1.5 px-4 mb-4 text-xs">
        <Plus size={12} /> ADD USER
      </button>
      <table>
        <thead><tr><th>Username</th><th>Role</th><th>Created</th><th>Last Login</th><th>Status</th></tr></thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td className="font-mono text-xs text-[#e8eaf0]">{u.username}</td>
              <td><span className="text-xs font-mono text-[#f59e0b]">{u.role}</span></td>
              <td className="font-mono text-xs text-[#4a5568]">{u.created_at?.slice(0, 10)}</td>
              <td className="font-mono text-xs text-[#4a5568]">{u.last_login?.slice(0, 16).replace('T', ' ') || '—'}</td>
              <td><span className={`text-xs font-mono ${u.is_active ? 'text-[#22c55e]' : 'text-[#4a5568]'}`}>{u.is_active ? 'ACTIVE' : 'INACTIVE'}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      {showAdd && (
        <Modal title="Add User" onClose={() => setShowAdd(false)}>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">Username</label>
              <input value={username} onChange={(e) => setUsername(e.target.value)} required />
            </div>
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">Role</label>
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                {['ADMIN', 'ANALYST', 'VIEWER'].map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
            <div className="flex gap-2 pt-2">
              <button type="submit" className="btn-primary py-1.5 px-5">CREATE USER</button>
              <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary py-1.5 px-5">CANCEL</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

function SystemTab() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/api/admin/system/status').then((r) => setStatus(r.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner label="Checking system status…" />
  if (!status) return <div className="text-[#f87171] font-mono text-sm">Failed to load system status</div>

  const rows = [
    { label: 'Ollama / LLM', value: status.ollama?.status, ok: status.ollama?.status === 'OK' },
    { label: 'ChromaDB Documents', value: status.chromadb?.document_count, ok: true },
    { label: 'SQLite Size', value: `${Math.round((status.sqlite?.size_bytes || 0) / 1024)} KB`, ok: true },
    { label: 'Total Messages', value: status.sqlite?.message_count, ok: true },
    { label: 'Active Channels', value: status.channels?.total_active, ok: true },
    { label: 'Channels Monitored', value: status.channels?.currently_monitoring, ok: true },
    { label: 'Users', value: status.users, ok: true },
  ]

  return (
    <div className="space-y-2">
      {rows.map(({ label, value, ok }) => (
        <div key={label} className="flex items-center justify-between py-2 border-b border-[#1f2330]">
          <span className="text-xs font-mono text-[#8892a4]">{label}</span>
          <span className={`text-xs font-mono font-bold ${ok ? 'text-[#22c55e]' : 'text-[#f87171]'}`}>{value ?? '—'}</span>
        </div>
      ))}
      <button
        onClick={() => { setLoading(true); api.get('/api/admin/system/status').then((r) => setStatus(r.data)).finally(() => setLoading(false)) }}
        className="btn-secondary flex items-center gap-2 py-1.5 px-4 text-xs mt-4"
      >
        <RefreshCw size={12} /> REFRESH
      </button>
    </div>
  )
}

export default function Settings() {
  const [tab, setTab] = useState('channels')
  const { isAdmin } = useAuth()

  const TABS = [
    { id: 'channels', label: 'Channels' },
    ...(isAdmin ? [{ id: 'users', label: 'Users' }] : []),
    { id: 'system', label: 'System' },
  ]

  return (
    <div>
      <div className="flex border-b border-[#1f2330] mb-5">
        {TABS.map((t) => (
          <Tab key={t.id} label={t.label} active={tab === t.id} onClick={() => setTab(t.id)} />
        ))}
      </div>
      {tab === 'channels' && <ChannelsTab />}
      {tab === 'users' && isAdmin && <UsersTab />}
      {tab === 'system' && <SystemTab />}
    </div>
  )
}
