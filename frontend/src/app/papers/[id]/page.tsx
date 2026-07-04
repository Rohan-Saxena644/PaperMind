'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Trash2, MessageSquare, BookOpen, Lightbulb, Tag, Save, Highlighter, ExternalLink, RotateCcw } from 'lucide-react'
import { Paper, ReadingStatus } from '@/types'
import api from '@/lib/api'
import StatusBadge from '@/components/papers/StatusBadge'
import ReadingStatusBadge from '@/components/papers/ReadingStatusBadge'

export default function PaperDetailPage() {
  const { id } = useParams()
  const router = useRouter()
  const [paper, setPaper] = useState<Paper | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeFlashcard, setActiveFlashcard] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [retrying, setRetrying] = useState(false)
  const [readingStatus, setReadingStatus] = useState<ReadingStatus>('unread')
  const [personalNotes, setPersonalNotes] = useState('')
  const [highlightsText, setHighlightsText] = useState('')
  const [savingProgress, setSavingProgress] = useState(false)
  const [progressMessage, setProgressMessage] = useState('')

  useEffect(() => {
    api.get(`/api/v1/papers/${id}`)
      .then(r => {
        setPaper(r.data)
        setReadingStatus(r.data.reading_status)
        setPersonalNotes(r.data.personal_notes || '')
        setHighlightsText((r.data.highlights || []).join('\n'))
      })
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

  const retryProcessing = async () => {
    if (!paper) return
    setRetrying(true)
    try {
      const { data } = await api.post(`/api/v1/papers/${paper.id}/retry`)
      setPaper(data)
    } finally {
      setRetrying(false)
    }
  }

  const saveReadingProgress = async () => {
    if (!paper) return
    setSavingProgress(true)
    setProgressMessage('')
    try {
      const highlights = highlightsText
        .split('\n')
        .map(item => item.trim())
        .filter(Boolean)

      const { data } = await api.patch(`/api/v1/papers/${paper.id}/reading`, {
        reading_status: readingStatus,
        personal_notes: personalNotes,
        highlights,
      })
      setPaper(data)
      setProgressMessage('Saved')
    } catch (err: any) {
      setProgressMessage(err.response?.data?.detail || 'Could not save progress.')
    } finally {
      setSavingProgress(false)
    }
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
          {paper.source_url && (
            <a
              href={paper.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs text-accent hover:underline mt-1"
            >
              <ExternalLink size={11} />
              Open original source
            </a>
          )}
          <div className="flex items-center gap-3 mt-2">
            <StatusBadge status={paper.status} />
            <ReadingStatusBadge status={paper.reading_status} />
            {paper.total_chunks > 0 && (
              <span className="text-xs text-muted">{paper.total_chunks} chunks indexed</span>
            )}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <Link href={`/chat?paper=${paper.id}`} className="btn-primary flex items-center gap-1.5 text-xs">
            <MessageSquare size={13} /> Ask AI
          </Link>
          {paper.status === 'failed' && (
            <button
              onClick={retryProcessing}
              disabled={retrying}
              className="btn-secondary inline-flex items-center gap-1.5 text-xs"
            >
              <RotateCcw size={13} />
              {retrying ? 'Retrying...' : 'Retry'}
            </button>
          )}
          <button onClick={handleDelete} disabled={deleting}
            className="p-2 text-muted hover:text-red-500 transition-colors rounded-lg hover:bg-red-50">
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {paper.status === 'failed' && paper.error_message && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 mb-6">
          <p className="font-medium mb-1">Processing failed after {paper.processing_attempts} attempt{paper.processing_attempts !== 1 ? 's' : ''}</p>
          <p>{paper.error_message}</p>
        </div>
      )}

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

      {/* Reading progress */}
      <div className="border border-parchment-border rounded-xl p-4 mb-6 bg-white">
        <div className="flex items-center justify-between gap-3 mb-4">
          <h3 className="text-sm font-medium text-navy flex items-center gap-1.5">
            <Highlighter size={14} className="text-accent" /> Reading progress
          </h3>
          <button
            onClick={saveReadingProgress}
            disabled={savingProgress}
            className="btn-primary inline-flex items-center gap-1.5 text-xs py-1.5"
          >
            <Save size={13} />
            {savingProgress ? 'Saving...' : 'Save'}
          </button>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-4">
          {(['unread', 'reading', 'done'] as ReadingStatus[]).map(status => (
            <button
              key={status}
              onClick={() => setReadingStatus(status)}
              className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
                readingStatus === status
                  ? 'border-accent bg-accent/10 text-accent font-medium'
                  : 'border-parchment-border text-muted hover:text-navy hover:bg-parchment/40'
              }`}
            >
              {status === 'unread' ? 'Unread' : status === 'reading' ? 'Reading' : 'Done'}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-navy">Personal notes</label>
            <textarea
              className="input mt-1 min-h-[96px] resize-y"
              value={personalNotes}
              onChange={(e) => setPersonalNotes(e.target.value)}
              placeholder="What should future-you remember about this paper?"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-navy">Highlights</label>
            <textarea
              className="input mt-1 min-h-[84px] resize-y"
              value={highlightsText}
              onChange={(e) => setHighlightsText(e.target.value)}
              placeholder="Add one highlight per line"
            />
          </div>
        </div>

        {progressMessage && (
          <p className={`text-xs mt-3 ${progressMessage === 'Saved' ? 'text-green-600' : 'text-red-600'}`}>
            {progressMessage}
          </p>
        )}
      </div>

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
