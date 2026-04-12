import { X } from 'lucide-react'
import { useEffect } from 'react'

export default function Modal({ title, onClose, children, wide = false }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      {/* Modal */}
      <div
        className={`relative bg-[#111318] border border-[#2d3447] rounded-lg shadow-2xl flex flex-col
          ${wide ? 'w-full max-w-3xl' : 'w-full max-w-md'}
          max-h-[90vh]`}
      >
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1f2330]">
          <h2 className="font-mono text-sm font-semibold text-[#e8eaf0] tracking-wide uppercase">
            {title}
          </h2>
          <button onClick={onClose} className="text-[#8892a4] hover:text-[#e8eaf0] transition-colors">
            <X size={16} />
          </button>
        </div>
        <div className="p-5 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}
