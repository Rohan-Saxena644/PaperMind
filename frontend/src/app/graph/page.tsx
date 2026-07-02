'use client'

import { useEffect, useState } from 'react'
import { Loader2, Network } from 'lucide-react'
import api from '@/lib/api'
import GraphView from '@/components/graph/GraphView'
import { GraphInsights, KnowledgeGraph } from '@/types'

export default function GraphPage() {
  const [graph, setGraph] = useState<KnowledgeGraph>({ nodes: [], edges: [] })
  const [insights, setInsights] = useState<GraphInsights | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get('/api/v1/graph/knowledge-map'),
      api.get('/api/v1/graph/insights'),
    ])
      .then(([graphResponse, insightsResponse]) => {
        setGraph(graphResponse.data)
        setInsights(insightsResponse.data)
      })
      .catch((err) => {
        setError(err.response?.data?.detail || 'Could not load the knowledge graph.')
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-6xl mx-auto px-8 py-10">
      <div className="flex items-start justify-between gap-6 mb-6">
        <div>
          <h2 className="font-display text-2xl text-navy">Knowledge graph</h2>
          <p className="text-muted text-sm mt-0.5">
            Concepts, papers, and authors extracted from your library
          </p>
        </div>
      </div>

      {loading ? (
        <div className="h-[560px] border border-parchment-border rounded-xl flex items-center justify-center">
          <Loader2 size={24} className="animate-spin text-accent" />
        </div>
      ) : error ? (
        <div className="border border-red-200 bg-red-50 text-red-700 rounded-xl px-4 py-3 text-sm">
          {error}
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-5">
          <GraphView nodes={graph.nodes} edges={graph.edges} />

          <aside className="space-y-4">
            <div className="border border-parchment-border rounded-xl p-4 bg-white">
              <div className="flex items-center gap-2 text-navy mb-3">
                <Network size={16} />
                <h3 className="text-sm font-medium">Library map</h3>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Stat label="Nodes" value={insights?.node_count ?? 0} />
                <Stat label="Connections" value={insights?.edge_count ?? 0} />
                <Stat label="Threads" value={insights?.research_thread_count ?? 0} />
                <Stat label="Density" value={insights?.density ?? 0} />
              </div>
            </div>

            <div className="border border-parchment-border rounded-xl p-4 bg-white">
              <h3 className="text-sm font-medium text-navy mb-3">Foundational concepts</h3>
              {insights?.top_concepts.length ? (
                <div className="space-y-2">
                  {insights.top_concepts.map(concept => (
                    <div key={concept.id} className="flex items-center justify-between gap-3 text-sm">
                      <span className="text-navy truncate">{concept.label}</span>
                      <span className="text-xs text-muted">{concept.centrality.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted">No concepts extracted yet.</p>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-parchment/50 px-3 py-2">
      <p className="text-lg font-semibold text-navy">{value}</p>
      <p className="text-xs text-muted">{label}</p>
    </div>
  )
}
