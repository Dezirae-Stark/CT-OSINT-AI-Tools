import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Radio, Search, GitBranch, Activity,
  Bell, FileText, Shield, Settings, LogOut, User
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'

const NAV = [
  { to: '/',         icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/search',   icon: Search,          label: 'Search' },
  { to: '/entities', icon: GitBranch,       label: 'Entity Map' },
  { to: '/timeline', icon: Activity,        label: 'Timeline' },
  { to: '/alerts',   icon: Bell,            label: 'Alert Rules' },
  { to: '/reports',  icon: FileText,        label: 'Reports' },
  { to: '/evidence', icon: Shield,          label: 'Evidence' },
  { to: '/settings', icon: Settings,        label: 'Settings' },
]

const ROLE_COLORS = { ADMIN: '#fb7185', ANALYST: '#f59e0b', VIEWER: '#60a5fa' }

export default function Sidebar() {
  const { username, role, logout } = useAuth()

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-60 flex flex-col border-r border-[#1f2330] bg-[#111318] z-40"
      style={{
        background: 'linear-gradient(180deg, #111318 0%, #0e1015 100%)',
      }}
    >
      {/* Scanline overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.5) 2px, rgba(255,255,255,0.5) 3px)',
        }}
      />

      {/* Logo */}
      <div className="px-5 py-5 border-b border-[#1f2330]">
        <div className="font-mono font-bold text-base text-[#e8eaf0] tracking-widest">
          GHOST<span className="text-[#3b82f6]">EXODUS</span>
        </div>
        <div className="text-[0.6rem] text-[#4a5568] tracking-[0.2em] mt-0.5 font-mono">
          OSINT PLATFORM
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-2.5 text-sm font-mono transition-all duration-150 relative
              ${isActive
                ? 'text-[#e8eaf0] bg-[#1a1d24] border-l-2 border-[#3b82f6]'
                : 'text-[#8892a4] hover:text-[#e8eaf0] hover:bg-[#1a1d24] border-l-2 border-transparent'
              }`
            }
          >
            <Icon size={15} strokeWidth={1.5} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User badge */}
      <div className="px-4 py-4 border-t border-[#1f2330]">
        <div className="flex items-center gap-2.5 mb-3">
          <div className="w-7 h-7 rounded bg-[#1a1d24] border border-[#2d3447] flex items-center justify-center">
            <User size={13} className="text-[#8892a4]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-mono text-[#e8eaf0] truncate">{username}</div>
            <div
              className="text-[0.6rem] font-mono font-bold tracking-wider"
              style={{ color: ROLE_COLORS[role] || '#8892a4' }}
            >
              {role}
            </div>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-[#8892a4] hover:text-[#f87171] border border-[#1f2330] hover:border-[#7f1d1d] rounded transition-all duration-150"
        >
          <LogOut size={12} />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
