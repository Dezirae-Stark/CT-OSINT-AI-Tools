import { useContext } from 'react'
import { FeedContext } from '../Layout/Layout'
import MessageCard from './MessageCard'

export default function LiveFeed({ messages = null }) {
  const ctx = useContext(FeedContext)
  const feed = messages || ctx?.liveMessages || []

  if (!feed.length) {
    return (
      <div className="text-center py-12 text-[#4a5568] text-xs font-mono">
        NO MESSAGES — AWAITING FEED
      </div>
    )
  }

  return (
    <div>
      {feed.map((msg, i) => (
        <MessageCard key={msg.id ?? i} message={msg} isNew={i === 0 && messages === null} />
      ))}
    </div>
  )
}
