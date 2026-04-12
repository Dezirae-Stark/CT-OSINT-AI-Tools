import { useEffect, useState } from 'react'
import { Plus, ToggleLeft, ToggleRight, Trash2, Play } from 'lucide-react'
import api from '../api/client'
import Modal from '../components/shared/Modal'
import Spinner from '../components/shared/Spinner'
import { useAuth } from '../hooks/useAuth'

const TRIGGER_TYPES = ['KEYWORD', 'ENTITY', 'FREQUENCY']
const ACTION_TYPES = ['ARCHIVE', 'NOTIFY', 'BOTH']

function RuleForm({ initial = {}, onSave, onCancel }) {
  const [name, setName] = useState(initial.name || '')
  const [triggerType, setTriggerType] = useState(initial.trigger_type || 'KEYWORD')
  const [triggerValue, setTriggerValue] = useState(initial.trigger_value || '')
  const [actionType, setActionType] = useState(initial.action_type || 'NOTIFY')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    if (!name || !triggerValue) { setError('Name and trigger value required'); return }
    setSaving(true)
    setError('')
    try {
      await onSave({ name, trigger_type: triggerType, trigger_value: triggerValue, action_type: actionType })
    } catch (e) {
      setError(e.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">Rule Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. UK Target Detection" />
      </div>
      <div>
        <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">Trigger Type</label>
        <select value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
          {TRIGGER_TYPES.map(t => <option key={t}>{t}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">
          {triggerType === 'FREQUENCY' ? 'N:M (e.g. 20:5 = 20 msgs in 5 min)' : 'Value / Regex'}
        </label>
        <input
          value={triggerValue}
          onChange={(e) => setTriggerValue(e.target.value)}
          placeholder={triggerType === 'FREQUENCY' ? '20:5' : triggerType === 'KEYWORD' ? 'regex or keyword' : '@username'}
          className="font-mono"
        />
      </div>
      <div>
        <label className="block text-xs font-mono text-[#8892a4] mb-1 uppercase tracking-wider">Action</label>
        <select value={actionType} onChange={(e) => setActionType(e.target.value)}>
          {ACTION_TYPES.map(a => <option key={a}>{a}</option>)}
        </select>
      </div>
      {error && <div className="text-xs font-mono text-[#f87171] bg-[#7f1d1d]/20 border border-[#7f1d1d]/40 px-3 py-2">{error}</div>}
      <div className="flex gap-2 pt-2">
        <button onClick={handleSave} disabled={saving} className="btn-primary py-1.5 px-5 disabled:opacity-50">
          {saving ? 'SAVING…' : 'SAVE RULE'}
        </button>
        <button onClick={onCancel} className="btn-secondary py-1.5 px-5">CANCEL</button>
      </div>
    </div>
  )
}

export default function AlertRules() {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(null)
  const { isAnalyst } = useAuth()

  const load = () => {
    api.get('/api/alerts/rules').then((r) => setRules(r.data || [])).finally(() => setLoading(false))
  }

  useEffect(load, [])

  const handleCreate = async (data) => {
    await api.post('/api/alerts/rules', data)
    setShowAdd(false)
    load()
  }

  const handleToggle = async (rule) => {
    await api.patch(`/api/alerts/rules/${rule.id}`, { is_active: !rule.is_active })
    load()
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this rule?')) return
    await api.delete(`/api/alerts/rules/${id}`)
    load()
  }

  const handleTest = async (id) => {
    setTesting(id)
    try {
      const r = await api.post(`/api/alerts/rules/${id}/test`)
      setTestResult(r.data)
    } catch (e) {
      console.error(e)
    } finally {
      setTesting(null)
    }
  }

  if (loading) return <div className="flex justify-center pt-20"><Spinner label="Loading rules…" /></div>

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div className="text-xs font-mono text-[#4a5568] uppercase tracking-wider">
          {rules.length} rule{rules.length !== 1 ? 's' : ''}
        </div>
        {isAnalyst && (
          <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2 py-1.5 px-4">
            <Plus size={13} /> ADD RULE
          </button>
        )}
      </div>

      {rules.length === 0
        ? <div className="text-center py-16 text-[#4a5568] font-mono">NO ALERT RULES CONFIGURED</div>
        : (
          <table>
            <thead>
              <tr>
                <th>Name</th><th>Type</th><th>Value</th><th>Action</th>
                <th>Last Triggered</th><th>Count</th><th>Status</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td className="font-mono text-xs text-[#e8eaf0]">{rule.name}</td>
                  <td><span className="text-xs font-mono text-[#6366f1]">{rule.trigger_type}</span></td>
                  <td className="font-mono text-xs text-[#8892a4] max-w-xs truncate">{rule.trigger_value}</td>
                  <td><span className="text-xs font-mono text-[#f59e0b]">{rule.action_type}</span></td>
                  <td className="font-mono text-xs text-[#4a5568]">
                    {rule.last_triggered ? rule.last_triggered.slice(0, 16).replace('T', ' ') : '—'}
                  </td>
                  <td className="font-mono text-xs text-[#8892a4]">{rule.trigger_count}</td>
                  <td>
                    <button onClick={() => handleToggle(rule)} disabled={!isAnalyst}>
                      {rule.is_active
                        ? <ToggleRight size={18} className="text-[#22c55e]" />
                        : <ToggleLeft size={18} className="text-[#4a5568]" />
                      }
                    </button>
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleTest(rule.id)}
                        disabled={testing === rule.id}
                        title="Test against recent messages"
                        className="text-[#4a5568] hover:text-[#3b82f6] disabled:opacity-40"
                      >
                        {testing === rule.id ? <Spinner size={12} /> : <Play size={12} />}
                      </button>
                      <button
                        onClick={() => handleDelete(rule.id)}
                        disabled={!isAnalyst}
                        className="text-[#4a5568] hover:text-[#f87171] disabled:opacity-40"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      }

      {showAdd && (
        <Modal title="Add Alert Rule" onClose={() => setShowAdd(false)}>
          <RuleForm onSave={handleCreate} onCancel={() => setShowAdd(false)} />
        </Modal>
      )}

      {testResult && (
        <Modal title={`Test Results — ${testResult.rule_name}`} onClose={() => setTestResult(null)}>
          <div className="space-y-3">
            <div className="text-sm font-mono">
              <span className="text-[#e8eaf0] font-bold">{testResult.match_count}</span>
              <span className="text-[#8892a4]"> matches out of {testResult.messages_tested} messages tested</span>
            </div>
            {testResult.matches?.slice(0, 5).map((m, i) => (
              <div key={i} className="text-xs font-mono bg-[#1a1d24] p-3">
                <div className="text-[#4a5568] mb-1">{m.timestamp_utc?.slice(0, 16)} UTC · <span className={`severity-badge severity-${m.severity}`}>{m.severity}</span></div>
                <div className="text-[#8892a4]">{m.content_preview?.slice(0, 200)}</div>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </div>
  )
}
