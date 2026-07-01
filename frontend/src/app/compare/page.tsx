'use client'

import { useEffect, useState } from 'react'
import { GitCompare, Check, X, Loader2, ArrowRight } from 'lucide-react'
import { PaperListItem, Comparison } from '@/types'
import api from '@/lib/api'

export default function ComparePage() {
  const [papers, setPapers] = useState<PaperListItem[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/api/v1/papers/').then(r => setPapers(r.data.filter((p: PaperListItem) => p.status === 'ready')))
  }, [])

  const toggle = (id: string) => {
    setSelected(prev => {
      if (prev.includes(id)) return prev.filter(p => p !== id)
      if (prev.length >= 4) return prev // cap at 4
      return [...prev, id]
    })
  }

  const runCompare = async () => {
    if (selected.length < 2) return
    setLoading(true)
    setError('')
    setComparison(null)
    try {
      const r = await api.post('/api/v1/papers/compare', { paper_ids: selected })
      setComparison(r.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Comparison failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-8 py-10">
      <div className="mb-6">
        <h2 className="font-display text-2xl text-navy flex items-center gap-2">
          <GitCompare size={22} className="text-accent" /> Compare papers
        </h2>
        <p className="text-muted text-sm mt-1">Select 2–4 papers to see how they relate.</p>
      </div>

      {papers.length < 2 ? (
        <div className="text-center py-12 border-2 border-dashed border-parchment-border rounded-xl">
          <p className="text-navy font-medium text-sm">Need at least 2 processed papers</p>
          <p className="text-muted text-xs mt-1">Upload more papers and wait for them to finish processing.</p>
        </div>
      ) : (
        <>
          {/* Paper selector */}
          <div className="grid grid-cols-2 gap-2 mb-5">
            {papers.map(paper => {
              const isSelected = selected.includes(paper.id)
              return (
                <button
                  key={paper.id}
                  onClick={() => toggle(paper.id)}
                  className={`text-left p-3 rounded-xl border transition-all flex items-start gap-2 ${
                    isSelected
                      ? 'border-accent bg-accent/5 shadow-sm'
                      : 'border-parchment-border hover:border-accent/40'
                  }`}
                >
                  <div className={`w-4 h-4 rounded mt-0.5 flex-shrink-0 flex items-center justify-center border ${
                    isSelected ? 'bg-accent border-accent' : 'border-parchment-border'
                  }`}>
                    {isSelected && <Check size={11} className="text-white" />}
                  </div>
                  <p className="text-xs font-medium text-navy leading-snug line-clamp-2">{paper.title}</p>
                </button>
              )
            })}
          </div>

          <button
            onClick={runCompare}
            disabled={selected.length < 2 || loading}
            className="btn-primary flex items-center gap-2 mb-8"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <GitCompare size={14} />}
            {loading ? 'Comparing…' : `Compare ${selected.length || ''} paper${selected.length !== 1 ? 's' : ''}`}
          </button>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2 mb-6">
              {error}
            </div>
          )}

          {/* Results */}
          {comparison && (
            <div className="space-y-6 animate-in fade-in">
              {/* Overview */}
              <div className="bg-parchment/60 border border-parchment-border rounded-xl p-4">
                <p className="text-sm text-navy/80 leading-relaxed">{comparison.overview}</p>
              </div>

              {/* Side by side: similarities / differences */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-green-700 mb-2 flex items-center gap-1.5">
                    <Check size={14} /> Similarities
                  </h3>
                  <ul className="space-y-1.5">
                    {comparison.similarities.map((s, i) => (
                      <li key={i} className="text-xs text-navy/70 flex gap-1.5">
                        <span className="text-green-500">•</span>{s}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-amber-700 mb-2 flex items-center gap-1.5">
                    <X size={14} /> Differences
                  </h3>
                  <ul className="space-y-1.5">
                    {comparison.differences.map((d, i) => (
                      <li key={i} className="text-xs text-navy/70 flex gap-1.5">
                        <span className="text-amber-500">•</span>{d}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Comparison table */}
              <div>
                <h3 className="text-sm font-medium text-navy mb-2">Side-by-side</h3>
                <div className="border border-parchment-border rounded-xl overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-parchment/60 border-b border-parchment-border">
                        <th className="text-left px-3 py-2 font-medium text-navy w-28">Aspect</th>
                        {comparison.paper_titles.map((t, i) => (
                          <th key={i} className="text-left px-3 py-2 font-medium text-navy">
                            <span className="line-clamp-1">{t}</span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {comparison.comparison_table.map((row, i) => (
                        <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-parchment/20'}>
                          <td className="px-3 py-2.5 font-medium text-navy align-top">{row.aspect}</td>
                          {row.values.map((v, j) => (
                            <td key={j} className="px-3 py-2.5 text-navy/70 align-top">{v}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Recommendation */}
              <div className="bg-accent/5 border border-accent/20 rounded-xl p-4 flex gap-2">
                <ArrowRight size={15} className="text-accent flex-shrink-0 mt-0.5" />
                <p className="text-sm text-navy/80">{comparison.recommendation}</p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
