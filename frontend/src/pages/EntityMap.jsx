import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap, useNodesState, useEdgesState
} from 'reactflow'
import 'reactflow/dist/style.css'
import api from '../api/client'
import Spinner from '../components/shared/Spinner'
import SeverityBadge from '../components/Feed/SeverityBadge'

function EntityPanel({ entity, onClose }) {
  if (!entity) return null
  return (
    <div className="absolute top-4 right-4 w-72 bg-[#111318] border border-[#2d3447] rounded-lg shadow-2xl z-10 p-4 overflow-y-auto max-h-[80vh]">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[0.6rem] font-mono text-[#4a5568] uppercase tracking-wider">{entity.type}</span>
        <button onClick={onClose} className="text-[#4a5568] hover:text-[#e8eaf0] text-xs">✕</button>
      </div>
      <div className="font-mono text-sm text-[#e8eaf0] font-bold mb-3 break-all">{entity.value}</div>

      <div className="space-y-2 text-xs font-mono text-[#8892a4]">
        <div>Occurrences: <span className="text-[#e8eaf0]">{entity.occurrences}</span></div>
        <div>First seen: <span className="text-[#e8eaf0]">{entity.first_seen?.slice(0, 10) || '—'}</span></div>
        <div>Last seen: <span className="text-[#e8eaf0]">{entity.last_seen?.slice(0, 10) || '—'}</span></div>
      </div>

      {entity.recent_messages?.length > 0 && (
        <div className="mt-4">
          <div className="text-[0.6rem] font-mono text-[#4a5568] uppercase tracking-wider mb-2">Recent Messages</div>
          {entity.recent_messages.slice(0, 3).map((m, i) => (
            <div key={m.id ?? i} className="mb-2 p-2 bg-[#1a1d24] text-xs font-body text-[#8892a4] rounded">
              <div className="flex items-center gap-2 mb-1">
                <SeverityBadge severity={m.severity} />
                <span className="text-[#4a5568]">{m.timestamp_utc?.slice(0, 10)}</span>
              </div>
              {m.content_preview?.slice(0, 100)}…
            </div>
          ))}
        </div>
      )}

      {entity.style_features && (
        <div className="mt-4">
          <div className="text-[0.6rem] font-mono text-[#4a5568] uppercase tracking-wider mb-2">Stylometry</div>
          <div className="text-xs font-mono text-[#8892a4] space-y-1">
            <div>Language: <span className="text-[#e8eaf0]">{entity.style_features.language}</span></div>
            <div>Vocab richness: <span className="text-[#e8eaf0]">{entity.style_features.vocabulary_richness}</span></div>
            <div>Avg sentence: <span className="text-[#e8eaf0]">{entity.style_features.avg_sentence_length} words</span></div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function EntityMap() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [selectedEntity, setSelectedEntity] = useState(null)

  useEffect(() => {
    api.get('/api/entities/graph').then((resp) => {
      const rawNodes = resp.data.nodes || []
      const rawEdges = resp.data.edges || []

      // Auto-layout (simple grid)
      const cols = Math.ceil(Math.sqrt(rawNodes.length))
      const laid = rawNodes.map((n, i) => ({
        ...n,
        position: {
          x: (i % cols) * 180 + Math.random() * 40,
          y: Math.floor(i / cols) * 120 + Math.random() * 40,
        },
        style: {
          background: n.style?.background || '#1a1d24',
          border: '1px solid #2d3447',
          borderRadius: 4,
          color: '#e8eaf0',
          fontSize: 10,
          fontFamily: 'IBM Plex Mono',
          padding: '4px 8px',
          minWidth: 80,
        },
      }))

      const styledEdges = rawEdges.map((e) => ({
        ...e,
        style: { stroke: '#2d3447', strokeWidth: Math.min(Number(e.style?.strokeWidth) || 1, 6) },
        labelStyle: { fill: '#4a5568', fontSize: 9 },
        labelBgStyle: { fill: '#111318' },
      }))

      setNodes(laid)
      setEdges(styledEdges)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  const onNodeClick = useCallback(async (_, node) => {
    try {
      const resp = await api.get(`/api/entities/${node.id}`)
      setSelectedEntity({
        ...resp.data,
        type: node.data?.type,
        value: node.data?.label,
        occurrences: node.data?.occurrences,
      })
    } catch (e) {
      console.error(e)
    }
  }, [])

  if (loading) return <div className="flex justify-center pt-20"><Spinner label="Loading entity graph…" /></div>

  return (
    <div className="h-[calc(100vh-8rem)] relative">
      <div className="text-xs font-mono text-[#4a5568] mb-2">
        {nodes.length} entities · {edges.length} relationships · Click a node to inspect
      </div>
      <div className="h-full border border-[#1f2330] rounded-lg overflow-hidden relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          style={{ background: '#0a0b0d' }}
        >
          <Background color="#1f2330" gap={24} size={1} />
          <Controls style={{ background: '#111318', border: '1px solid #1f2330' }} />
          <MiniMap
            style={{ background: '#111318', border: '1px solid #1f2330' }}
            nodeColor={(n) => n.style?.background || '#1a1d24'}
          />
        </ReactFlow>
        {selectedEntity && (
          <EntityPanel entity={selectedEntity} onClose={() => setSelectedEntity(null)} />
        )}
      </div>
    </div>
  )
}
