import { useEffect, useState, useContext } from 'react'
import { Radio, AlertTriangle, Globe, Flag } from 'lucide-react'
import { PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis, ResponsiveContainer } from 'recharts'
import api from '../api/client'
import MessageCard from '../components/Feed/MessageCard'
import Spinner from '../components/shared/Spinner'
import { FeedContext } from '../components/Layout/Layout'

const SEV_COLORS = {
  NONE: '#9ca3af', LOW: '#60a5fa', MEDIUM: '#f59e0b', HIGH: '#f87171', CRITICAL: '#fb7185'
}

function StatCard({ label, value, icon: Icon, color = '#3b82f6' }) {
  return (
    <div className="card flex items-center gap-4">
      <div className="w-10 h-10 rounded flex items-center justify-center" style={{ background: `${color}20` }}>
        <Icon size={18} style={{ color }} />
      </div>
      <div>
        <div className="text-2xl font-mono font-bold text-[#e8eaf0]">{value ?? '—'}</div>
        <div className="text-[0.65rem] font-mono text-[#4a5568] uppercase tracking-wider">{label}</div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [feed, setFeed] = useState([])
  const [stats, setStats] = useState(null)
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const ctx = useContext(FeedContext)

  useEffect(() => {
    Promise.all([
      api.get('/api/feed?limit=30&severity=LOW'),
      api.get('/api/channels'),
    ]).then(([feedResp, channelResp]) => {
      setFeed(feedResp.data.messages || [])
      setChannels(channelResp.data || [])

      // Compute stats from feed
      const today = new Date().toISOString().slice(0, 10)
      const msgs = feedResp.data.messages || []
      const todayMsgs = msgs.filter(m => m.timestamp_utc?.startsWith(today))
      const highCrit = msgs.filter(m => ['HIGH', 'CRITICAL'].includes(m.severity))

      setStats({
        today: todayMsgs.length,
        active_alerts: highCrit.length,
        channels: channelResp.data?.length || 0,
        high_crit: highCrit.length,
      })
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  // Merge live feed
  const liveMsgs = ctx?.liveMessages || []
  const allMsgs = [...liveMsgs, ...feed].slice(0, 50)

  // Severity distribution for donut
  const sevCounts = allMsgs.reduce((acc, m) => {
    acc[m.severity] = (acc[m.severity] || 0) + 1
    return acc
  }, {})
  const donutData = Object.entries(sevCounts).map(([name, value]) => ({ name, value }))

  // Top channels
  const chCounts = allMsgs.reduce((acc, m) => {
    acc[m.channel_name] = (acc[m.channel_name] || 0) + 1
    return acc
  }, {})
  const barData = Object.entries(chCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, count]) => ({ name: name.slice(0, 16), count }))

  if (loading) return <div className="flex justify-center pt-20"><Spinner label="Loading dashboard…" /></div>

  return (
    <div className="space-y-5">
      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Messages Today" value={stats?.today} icon={Radio} color="#3b82f6" />
        <StatCard label="Active Alerts (24h)" value={stats?.active_alerts} icon={AlertTriangle} color="#f59e0b" />
        <StatCard label="Channels Monitored" value={stats?.channels} icon={Globe} color="#6366f1" />
        <StatCard label="High / Critical Flags" value={stats?.high_crit} icon={Flag} color="#f87171" />
      </div>

      {/* Main columns */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-5">
        {/* Live Feed — 3/5 width */}
        <div className="xl:col-span-3">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-mono uppercase tracking-widest text-[#8892a4]">Live Feed</h2>
            <div className="flex items-center gap-1.5 text-[0.6rem] font-mono text-[#22c55e]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] animate-pulse" />
              LIVE
            </div>
          </div>
          <div className="space-y-0 max-h-[70vh] overflow-y-auto pr-1">
            {allMsgs.length === 0
              ? <div className="text-center py-12 text-[#4a5568] text-xs font-mono">AWAITING MESSAGES</div>
              : allMsgs.map((m, i) => (
                  <MessageCard
                    key={m.id ?? i}
                    message={m}
                    isNew={i === 0 && liveMsgs.length > 0 && i < liveMsgs.length}
                  />
                ))
            }
          </div>
        </div>

        {/* Right panels — 2/5 */}
        <div className="xl:col-span-2 space-y-4">
          {/* Severity donut */}
          <div className="card">
            <div className="text-[0.65rem] font-mono uppercase tracking-widest text-[#4a5568] mb-3">
              Severity Distribution
            </div>
            {donutData.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={donutData} dataKey="value" cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={2}>
                    {donutData.map((entry) => (
                      <Cell key={entry.name} fill={SEV_COLORS[entry.name] || '#374151'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#111318', border: '1px solid #1f2330', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
                    labelStyle={{ color: '#e8eaf0' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-8 text-[#4a5568] text-xs font-mono">NO DATA</div>
            )}
          </div>

          {/* Top channels bar */}
          <div className="card">
            <div className="text-[0.65rem] font-mono uppercase tracking-widest text-[#4a5568] mb-3">
              Top Active Channels (24h)
            </div>
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={barData} layout="vertical" margin={{ left: 0, right: 8, top: 0, bottom: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fontFamily: 'IBM Plex Mono', fill: '#8892a4' }} width={90} />
                  <Bar dataKey="count" fill="#3b82f6" radius={[0, 2, 2, 0]} />
                  <Tooltip
                    contentStyle={{ background: '#111318', border: '1px solid #1f2330', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-8 text-[#4a5568] text-xs font-mono">NO DATA</div>
            )}
          </div>

          {/* Recent LLM classifications */}
          <div className="card">
            <div className="text-[0.65rem] font-mono uppercase tracking-widest text-[#4a5568] mb-3">
              Recent LLM Classifications
            </div>
            <div className="space-y-2">
              {allMsgs
                .filter(m => m.llm_classification)
                .slice(0, 5)
                .map((m, i) => {
                  const cls = m.llm_classification
                  return (
                    <div key={m.id ?? i} className="flex items-center justify-between text-xs font-mono py-1 border-b border-[#1f2330] last:border-0">
                      <span className="text-[#8892a4] truncate max-w-[60%]">
                        {cls?.threat_category || 'UNKNOWN'}
                      </span>
                      <span className={`severity-badge severity-${cls?.severity || 'NONE'}`}>
                        {cls?.severity || '—'}
                      </span>
                    </div>
                  )
                })}
              {allMsgs.filter(m => m.llm_classification).length === 0 && (
                <div className="text-[#4a5568] text-xs text-center py-3">NO CLASSIFICATIONS YET</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
