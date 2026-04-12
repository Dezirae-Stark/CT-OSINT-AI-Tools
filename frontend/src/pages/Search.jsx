import { useState } from 'react'
import { Search as SearchIcon, Filter } from 'lucide-react'
import api from '../api/client'
import MessageCard from '../components/Feed/MessageCard'
import Spinner from '../components/shared/Spinner'

const MODES = ['SEMANTIC', 'KEYWORD', 'ENTITY', 'RAG']
const SEVERITIES = ['', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

export default function Search() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('SEMANTIC')
  const [severity, setSeverity] = useState('')
  const [results, setResults] = useState(null)
  const [ragAnswer, setRagAnswer] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError('')
    setResults(null)
    setRagAnswer(null)
    try {
      const filters = severity ? { severity } : null
      const resp = await api.post('/api/search', {
        query: query.trim(),
        mode,
        filters,
        limit: 30,
      })
      if (mode === 'RAG') {
        setRagAnswer(resp.data)
      } else {
        setResults(resp.data.results || [])
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <form onSubmit={handleSearch} className="space-y-4 mb-6">
        {/* Search bar */}
        <div className="relative">
          <SearchIcon size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#4a5568]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search messages, entities, or ask a question…"
            className="pl-10 text-base py-3"
            autoFocus
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <Filter size={12} className="text-[#4a5568]" />
            <span className="text-xs font-mono text-[#4a5568] uppercase tracking-wider">Mode:</span>
          </div>
          {MODES.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`text-xs font-mono px-3 py-1 rounded border transition-all
                ${mode === m
                  ? 'border-[#3b82f6] text-[#3b82f6] bg-[#1e3a5f]/30'
                  : 'border-[#1f2330] text-[#8892a4] hover:border-[#2d3447]'
                }`}
            >
              {m}
            </button>
          ))}

          <div className="ml-4">
            <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="text-xs w-auto py-1 px-2">
              <option value="">All Severities</option>
              {SEVERITIES.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <button type="submit" disabled={loading} className="btn-primary ml-auto py-1.5 px-6 disabled:opacity-50">
            {loading ? 'SEARCHING…' : 'SEARCH'}
          </button>
        </div>
      </form>

      {/* Loading */}
      {loading && <div className="flex justify-center py-12"><Spinner label={mode === 'RAG' ? 'Analysing…' : 'Searching…'} /></div>}

      {/* Error */}
      {error && (
        <div className="text-sm font-mono text-[#f87171] bg-[#7f1d1d]/20 border border-[#7f1d1d]/40 px-4 py-3 mb-4">
          {error}
        </div>
      )}

      {/* RAG answer */}
      {ragAnswer && (
        <div className="mb-6 space-y-4">
          <div className="card border-[#2d3447]">
            <div className="text-[0.6rem] font-mono uppercase tracking-widest text-[#3b82f6] mb-2">
              AI Intelligence Analysis
            </div>
            <p className="text-sm font-body text-[#e8eaf0] leading-relaxed whitespace-pre-wrap">
              {ragAnswer.answer}
            </p>
          </div>
          {ragAnswer.sources?.length > 0 && (
            <div>
              <div className="text-xs font-mono text-[#4a5568] uppercase tracking-wider mb-2">
                Source Documents ({ragAnswer.sources.length})
              </div>
              {ragAnswer.sources.map((s, i) => (
                <div key={i} className="card mb-2 text-xs font-mono">
                  <div className="text-[#8892a4] mb-1 line-clamp-2">{s.content}</div>
                  <div className="text-[#4a5568]">Score: {s.score}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Results */}
      {results !== null && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-mono text-[#4a5568] uppercase tracking-wider">
              {results.length} result{results.length !== 1 ? 's' : ''} — {mode} search
            </div>
          </div>
          {results.length === 0
            ? <div className="text-center py-12 text-[#4a5568] font-mono text-sm">NO RESULTS FOUND</div>
            : results.map((m, i) => (
                <div key={i}>
                  {m.relevance_score !== undefined && (
                    <div className="text-[0.6rem] font-mono text-[#4a5568] mb-0.5 text-right">
                      relevance: {(m.relevance_score * 100).toFixed(1)}%
                    </div>
                  )}
                  <MessageCard message={{ ...m, id: m.message_id }} />
                </div>
              ))
          }
        </div>
      )}
    </div>
  )
}
