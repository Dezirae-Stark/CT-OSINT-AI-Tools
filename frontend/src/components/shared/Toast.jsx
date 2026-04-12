export default function Toast({ message, type = 'info' }) {
  const colors = {
    info:  'border-[#3b82f6] text-[#60a5fa]',
    alert: 'border-[#f87171] text-[#fb7185]',
    success: 'border-[#22c55e] text-[#4ade80]',
  }
  return (
    <div className={`bg-[#111318] border-l-2 ${colors[type] || colors.info} px-4 py-2.5 text-xs font-mono shadow-lg max-w-xs feed-item-enter`}>
      {message}
    </div>
  )
}
