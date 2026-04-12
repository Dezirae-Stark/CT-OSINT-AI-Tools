import { useEffect, useState } from 'react'
import { Shield, CheckCircle, AlertOctagon, Download, Copy } from 'lucide-react'
import api from '../api/client'
import Spinner from '../components/shared/Spinner'
import Modal from '../components/shared/Modal'
import { useAuth } from '../hooks/useAuth'

const SEVERITIES = ['', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

export default function Evidence() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [severity, setSeverity] = useState('')
  const [verifying, setVerifying] = useState(null)
  const [selected, setSelected] = useState(new Set())
  const [showExport, setShowExport] = useState(false)
  const [caseRef, setCaseRef] = useState('')
  const [exporting, setExporting] = useState(false)
  const [auditLog, setAuditLog] = useState([])
  const { isAnalyst } = useAuth()

  const load = () => {
    const params = severity ? `?severity=${severity}` : ''
    api.get(`/api/evidence${params}`).then((r) => {
      setItems(r.data.items || [])
    }).finally(() => setLoading(false))
  }

  useEffect(load, [severity])

  const handleVerify = async (manifestId) => {
    setVerifying(manifestId)
    try {
      const r = await api.get(`/api/evidence/${manifestId}/verify`)
      setItems((prev) => prev.map((item) =>
        item.manifest_id === manifestId
          ? { ...item, verification_status: r.data.status }
          : item
      ))
    } finally {
      setVerifying(null)
    }
  }

  const handleExport = async () => {
    if (!caseRef) return
    setExporting(true)
    try {
      const messageIds = items
        .filter((item) => selected.has(item.manifest_id))
        .map((item) => item.message_id)
      const resp = await api.post('/api/evidence/export-bundle', {
        case_reference: caseRef,
        message_ids: messageIds,
      }, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `ghostexodus_${caseRef.replace(/\s+/g, '_')}.zip`
      a.click()
      URL.revokeObjectURL(url)
      setShowExport(false)
      setSelected(new Set())
      setCaseRef('')
    } catch (e) {
      console.error(e)
    } finally {
      setExporting(false)
    }
  }

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const selectAll = () => setSelected(new Set(items.map(i => i.manifest_id)))
  const clearAll = () => setSelected(new Set())

  const copyHash = (hash) => {
    navigator.clipboard.writeText(hash).catch(console.error)
  }

  if (loading) return <div className="flex justify-center pt-20"><Spinner label="Loading evidence…" /></div>

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="w-auto py-1.5 text-xs">
          {SEVERITIES.map(s => <option key={s} value={s}>{s || 'All Severities'}</option>)}
        </select>
        <div className="text-xs font-mono text-[#4a5568]">{items.length} records</div>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={selectAll} className="text-xs font-mono text-[#8892a4] hover:text-[#e8eaf0]">Select All</button>
          <button onClick={clearAll} className="text-xs font-mono text-[#8892a4] hover:text-[#e8eaf0]">Clear</button>
          {selected.size > 0 && isAnalyst && (
            <button onClick={() => setShowExport(true)} className="btn-primary flex items-center gap-1.5 py-1.5 px-4 text-xs">
              <Download size={12} /> Export Bundle ({selected.size})
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      {items.length === 0
        ? <div className="text-center py-16 text-[#4a5568] font-mono">NO EVIDENCE RECORDS</div>
        : (
          <table>
            <thead>
              <tr>
                <th className="w-8"><input type="checkbox" onChange={(e) => e.target.checked ? selectAll() : clearAll()} /></th>
                <th>Manifest ID</th><th>Message ID</th><th>Channel</th>
                <th>Captured UTC</th><th>SHA-256</th><th>Severity</th>
                <th>Integrity</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.manifest_id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(item.manifest_id)}
                      onChange={() => toggleSelect(item.manifest_id)}
                    />
                  </td>
                  <td className="font-mono text-xs text-[#4a5568]">{item.manifest_id}</td>
                  <td className="font-mono text-xs text-[#8892a4]">{item.message_id}</td>
                  <td className="text-xs text-[#e8eaf0]">{item.channel_name}</td>
                  <td className="font-mono text-xs text-[#4a5568]">{item.captured_at_utc?.slice(0, 16).replace('T', ' ')}</td>
                  <td>
                    <div className="flex items-center gap-1.5">
                      <span className="hash-text">{item.sha256_short}…</span>
                      <button onClick={() => copyHash(item.sha256_hash)} className="text-[#4a5568] hover:text-[#3b82f6]">
                        <Copy size={10} />
                      </button>
                    </div>
                  </td>
                  <td><span className={`severity-badge severity-${item.severity}`}>{item.severity}</span></td>
                  <td>
                    {item.verification_status === 'VERIFIED' && (
                      <span className="flex items-center gap-1 text-[0.65rem] font-mono text-[#22c55e]">
                        <CheckCircle size={10} /> VERIFIED
                      </span>
                    )}
                    {item.verification_status === 'TAMPERED' && (
                      <span className="flex items-center gap-1 text-[0.65rem] font-mono text-[#f87171]">
                        <AlertOctagon size={10} /> TAMPERED
                      </span>
                    )}
                    {!item.verification_status && (
                      <span className="text-[0.65rem] font-mono text-[#4a5568]">—</span>
                    )}
                  </td>
                  <td>
                    <button
                      onClick={() => handleVerify(item.manifest_id)}
                      disabled={verifying === item.manifest_id}
                      className="flex items-center gap-1 text-xs font-mono text-[#4a5568] hover:text-[#3b82f6] disabled:opacity-40"
                    >
                      {verifying === item.manifest_id ? <Spinner size={10} /> : <Shield size={10} />}
                      Verify
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      }

      {/* Export modal */}
      {showExport && (
        <Modal title={`Export Case Bundle (${selected.size} items)`} onClose={() => setShowExport(false)}>
          <div className="space-y-4">
            <div className="text-xs font-mono text-[#8892a4]">
              This will generate a ZIP containing all evidence files, SHA-256 manifest, chain of custody record, and verification script.
            </div>
            <div>
              <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">Case Reference</label>
              <input value={caseRef} onChange={(e) => setCaseRef(e.target.value)} placeholder="CASE-2024-001" required />
            </div>
            <div className="flex gap-2 pt-2">
              <button onClick={handleExport} disabled={!caseRef || exporting} className="btn-primary py-1.5 px-5 disabled:opacity-50">
                {exporting ? 'GENERATING…' : 'EXPORT ZIP'}
              </button>
              <button onClick={() => setShowExport(false)} className="btn-secondary py-1.5 px-5">CANCEL</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
