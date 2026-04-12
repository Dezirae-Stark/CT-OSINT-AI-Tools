import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import api from '../api/client'
import Spinner from '../components/shared/Spinner'

const SEV_COLORS = { NONE: '#9ca3af', LOW: '#60a5fa', MEDIUM: '#f59e0b', HIGH: '#f87171', CRITICAL: '#fb7185' }
const LINE_COLORS = ['#3b82f6', '#6366f1', '#ec4899', '#22c55e', '#f59e0b']

export default function Timeline() {
  const [data, setData] = useState(null)
  const [hourly, setHourly] = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(14)
  const [granularity, setGranularity] = useState('day')

  useEffect(() => {
    setLoading(true)
    const end = new Date().toISOString().slice(0, 10)
    const start = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10)

    Promise.all([
      api.get(`/api/timeline?start=${start}&end=${end}&granularity=${granularity}`),
      api.get(`/api/timeline/hourly?days=${days}`),
    ]).then(([timelineResp, hourlyResp]) => {
      setData(timelineResp.data)
      setHourly(hourlyResp.data)
    }).catch(console.error).finally(() => setLoading(false))
  }, [days, granularity])

  if (loading) return <div className="flex justify-center pt-20"><Spinner label="Loading timeline…" /></div>

  const severitySeries = data?.severity_series || []
  const channelSeries = data?.channel_series || []
  const hourDist = hourly?.distribution || []

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="text-xs font-mono text-[#4a5568] uppercase tracking-wider">Period:</div>
        {[7, 14, 30, 60].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`text-xs font-mono px-3 py-1 rounded border transition-all
              ${days === d ? 'border-[#3b82f6] text-[#3b82f6]' : 'border-[#1f2330] text-[#8892a4]'}`}
          >
            {d}d
          </button>
        ))}
        <div className="ml-4 text-xs font-mono text-[#4a5568] uppercase tracking-wider">Granularity:</div>
        {['day', 'hour'].map((g) => (
          <button
            key={g}
            onClick={() => setGranularity(g)}
            className={`text-xs font-mono px-3 py-1 rounded border transition-all
              ${granularity === g ? 'border-[#3b82f6] text-[#3b82f6]' : 'border-[#1f2330] text-[#8892a4]'}`}
          >
            {g.toUpperCase()}
          </button>
        ))}
        <div className="ml-auto text-xs font-mono text-[#4a5568]">
          {data?.total_messages || 0} messages total
        </div>
      </div>

      {/* Posting frequency by channel */}
      {channelSeries.length > 0 && (
        <div className="card">
          <div className="text-[0.65rem] font-mono uppercase tracking-widest text-[#4a5568] mb-4">
            Posting Frequency by Channel
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2330" />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#4a5568', fontFamily: 'IBM Plex Mono' }} />
              <YAxis tick={{ fontSize: 9, fill: '#4a5568', fontFamily: 'IBM Plex Mono' }} />
              <Tooltip
                contentStyle={{ background: '#111318', border: '1px solid #1f2330', fontFamily: 'IBM Plex Mono', fontSize: 11 }}
              />
              <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
              {channelSeries.map((ch, i) => (
                <Line
                  key={ch.channel_id}
                  data={ch.data}
                  dataKey="count"
                  name={ch.channel_name}
                  stroke={LINE_COLORS[i % LINE_COLORS.length]}
                  dot={false}
                  strokeWidth={1.5}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Severity over time */}
      {severitySeries.length > 0 && (
        <div className="card">
          <div className="text-[0.65rem] font-mono uppercase tracking-widest text-[#4a5568] mb-4">
            Severity Distribution Over Time
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={severitySeries} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2330" />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#4a5568', fontFamily: 'IBM Plex Mono' }} />
              <YAxis tick={{ fontSize: 9, fill: '#4a5568', fontFamily: 'IBM Plex Mono' }} />
              <Tooltip
                contentStyle={{ background: '#111318', border: '1px solid #1f2330', fontFamily: 'IBM Plex Mono', fontSize: 11 }}
              />
              {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
                <Area
                  key={sev}
                  type="monotone"
                  dataKey={sev}
                  stackId="1"
                  stroke={SEV_COLORS[sev]}
                  fill={SEV_COLORS[sev]}
                  fillOpacity={0.4}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Hourly UTC distribution */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="text-[0.65rem] font-mono uppercase tracking-widest text-[#4a5568]">
            UTC Hourly Activity Distribution
          </div>
          {hourly && (
            <div className="text-xs font-mono text-[#8892a4]">
              Peak hour: <span className="text-[#f59e0b]">{String(hourly.peak_hour_utc).padStart(2, '0')}:00 UTC</span>
              {' · '}Likely TZ offset: <span className="text-[#60a5fa]">
                {hourly.likely_tz_offset_hours >= 0 ? '+' : ''}{hourly.likely_tz_offset_hours}h
              </span>
            </div>
          )}
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={hourDist} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2330" />
            <XAxis dataKey="hour_utc" tick={{ fontSize: 8, fill: '#4a5568', fontFamily: 'IBM Plex Mono' }}
              tickFormatter={(h) => `${String(h).padStart(2, '0')}:00`}
            />
            <YAxis tick={{ fontSize: 9, fill: '#4a5568', fontFamily: 'IBM Plex Mono' }} />
            <Tooltip
              contentStyle={{ background: '#111318', border: '1px solid #1f2330', fontFamily: 'IBM Plex Mono', fontSize: 11 }}
              labelFormatter={(l) => `${String(l).padStart(2, '0')}:00 UTC`}
            />
            <Bar dataKey="count" fill="#6366f1" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
