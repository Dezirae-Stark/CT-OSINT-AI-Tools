import { useState } from 'react'
import { Eye, Archive, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'
import SeverityBadge from './SeverityBadge'
import api from '../../api/client'

function highlightKeywords(text, keywords) {
  if (!keywords?.length || !text) return text
  let result = text
  keywords.forEach(({ keyword }) => {
    if (!keyword) return
    try {
      const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
      result = result.replace(regex, `<mark class="bg-amber-900/60 text-amber-300 px-0.5">$1</mark>`)
    } catch { /* skip invalid regex */ }
  })
  return result
}

export default function MessageCard({ message, onAction, isNew = false }) {
  const [expanded, setExpanded] = useState(false)
  const [escalating, setEscalating] = useState(false)
  const content = message.content_text || message.content_preview || ''
  const preview = content.length > 200 ? content.slice(0, 200) + '…' : content
  const keywords = message.flagged_keywords || []
  const displayText = expanded ? content : preview

  const handleEscalate = async () => {
    setEscalating(true)
    try {
      await api.patch(`/api/messages/${message.id}/severity`, { severity: 'CRITICAL' })
      onAction?.('escalated', message.id)
    } catch (e) {
      console.error(e)
    } finally {
      setEscalating(false)
    }
  }

  const handleArchive = async () => {
    try {
      await api.patch(`/api/messages/${message.id}/severity`, { severity: message.severity })
      onAction?.('archived', message.id)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div
      className={`card mb-2 transition-all duration-150 hover:border-[#2d3447] ${isNew ? 'feed-item-enter' : ''}`}
    >
      {/* Header row */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <SeverityBadge severity={message.severity} />
        <span className="text-xs font-mono text-[#3b82f6]">{message.channel_name}</span>
        <span className="text-xs font-mono text-[#4a5568]">#{message.telegram_message_id}</span>
        {message.sender_username && (
          <span className="text-xs font-mono text-[#8892a4]">@{message.sender_username}</span>
        )}
        <span className="ml-auto text-xs font-mono text-[#4a5568]">
          {new Date(message.timestamp_utc).toISOString().slice(0, 19).replace('T', ' ')} UTC
        </span>
      </div>

      {/* Content */}
      <div
        className="text-sm text-[#8892a4] font-body leading-relaxed mb-2"
        dangerouslySetInnerHTML={{ __html: highlightKeywords(displayText, keywords) }}
      />

      {/* Expand button */}
      {content.length > 200 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-[#4a5568] hover:text-[#8892a4] mb-2"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? 'Show less' : 'Show full'}
        </button>
      )}

      {/* Keywords */}
      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {keywords.slice(0, 5).map((k, i) => (
            <span
              key={k.keyword ?? i}
              className="text-[0.6rem] font-mono px-1.5 py-0.5 bg-amber-900/20 text-amber-500 border border-amber-900/40"
            >
              {k.keyword}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-[#1f2330]">
        <button
          onClick={() => window.open(`/api/messages/${message.id}`, '_blank')}
          className="flex items-center gap-1 text-xs font-mono text-[#8892a4] hover:text-[#3b82f6] transition-colors"
        >
          <Eye size={11} /> View Full
        </button>
        <button
          onClick={handleArchive}
          className="flex items-center gap-1 text-xs font-mono text-[#8892a4] hover:text-[#60a5fa] transition-colors"
        >
          <Archive size={11} /> Archive
        </button>
        <button
          onClick={handleEscalate}
          disabled={escalating || message.severity === 'CRITICAL'}
          className="flex items-center gap-1 text-xs font-mono text-[#8892a4] hover:text-[#fb7185] transition-colors disabled:opacity-40"
        >
          <AlertTriangle size={11} /> Escalate
        </button>
        {message.forwarded_from && (
          <span className="ml-auto text-xs font-mono text-[#4a5568]">
            ↩ fwd: {message.forwarded_from}
          </span>
        )}
      </div>
    </div>
  )
}
