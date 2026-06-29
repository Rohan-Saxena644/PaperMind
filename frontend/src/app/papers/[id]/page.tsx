'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Trash2, MessageSquare, BookOpen, Lightbulb, Tag } from 'lucide-react'
import { Paper } from '@/types'
import api from '@/lib/api'
import StatusBadge from '@/components/papers/StatusBadge'

export default function PaperDetailPage() {
  const { id } = useParams()
  const router = useRouter()
  const [paper, setPaper] = useState<Paper | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeFlashcard, setActiveFlashcard] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    api.get(`/api/v1/papers/${id}`)
      .then(r => setPaper(r.data))
      .catch(() => router.push('/papers'))
      .finally(() => setLoading(false))
  }, [id, router])

  const handleDelete = async () => {
    if (!confirm('Delete this paper and all its embeddings?')) return
    setDeleting(true)
    try {
      await api.delete(`/api/v1/papers/${id}`)
      router.push('/papers')
    } catch { setDeleting(false) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full text-muted text-sm">Loading…</div>
  )
  if (!paper) return null

  return (
    <div className="max-w-2xl mx-auto px-8 py-10">
      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <Link href="/papers" className="mt-1 text-muted hover:text-navy transition-colors">
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1 min-w-0">
          <h2 className="font-display text-2xl text-navy leading-snug">{paper.title}</h2>
          {paper.authors && <p className="text-sm text-muted mt-1">{paper.authors}</p>}
          <div className="flex items-center gap-3 mt-2">
            <StatusBadge status={paper.status} />
            {paper.total_chunks > 0 && (
              <span className="text-xs text-muted">{paper.total_chunks} chunks indexed</span>
            )}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <Link href={`/chat?paper=${paper.id}`} className="btn-primary flex items-center gap-1.5 text-xs">
            <MessageSquare size={13} /> Ask AI
          </Link>
          <button onClick={handleDelete} disabled={deleting}
            className="p-2 text-muted hover:text-red-500 transition-colors rounded-lg hover:bg-red-50">
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {/* Keywords */}
      {paper.keywords && paper.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-6">
          {paper.keywords.map(kw => (
            <span key={kw} className="inline-flex items-center gap-1 text-xs bg-accent/8 text-accent px-2 py-0.5 rounded-full border border-accent/20">
              <Tag size={10} /> {kw}
            </span>
          ))}
        </div>
      )}

      {/* Summary */}
      {paper.summary_short && (
        <div className="bg-parchment/60 border border-parchment-border rounded-xl p-4 mb-5">
          <p className="text-sm font-medium text-navy mb-1 flex items-center gap-1.5">
            <BookOpen size={14} /> One-line summary
          </p>
          <p className="text-sm text-navy/80 italic">"{paper.summary_short}"</p>
        </div>
      )}

      {paper.summary_long && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-navy mb-2">Summary</h3>
          <p className="text-sm text-navy/70 leading-relaxed whitespace-pre-line">{paper.summary_long}</p>
        </div>
      )}

      {/* Key Contributions */}
      {paper.key_contributions && paper.key_contributions.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-navy mb-2 flex items-center gap-1.5">
            <Lightbulb size={14} className="text-amber-500" /> Key contributions
          </h3>
          <ul className="space-y-2">
            {paper.key_contributions.map((c, i) => (
              <li key={i} className="flex gap-2 text-sm text-navy/70">
                <span className="text-accent font-mono text-xs mt-0.5 flex-shrink-0">{String(i + 1).padStart(2, '0')}</span>
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Flashcards */}
      {paper.flashcards && paper.flashcards.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-navy mb-3">Flashcards ({paper.flashcards.length})</h3>
          <div className="space-y-2">
            {paper.flashcards.map((fc, i) => (
              <div key={i}
                className="border border-parchment-border rounded-xl overflow-hidden cursor-pointer"
                onClick={() => setActiveFlashcard(activeFlashcard === i ? null : i)}>
                <div className="px-4 py-3 bg-parchment/40 flex items-start gap-2">
                  <span className="text-xs font-mono text-accent mt-0.5 flex-shrink-0">Q</span>
                  <p className="text-sm text-navy">{fc.question}</p>
                </div>
                {activeFlashcard === i && (
                  <div className="px-4 py-3 border-t border-parchment-border bg-white flex items-start gap-2">
                    <span className="text-xs font-mono text-green-600 mt-0.5 flex-shrink-0">A</span>
                    <p className="text-sm text-navy/80">{fc.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
