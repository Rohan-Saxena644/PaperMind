'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { BookOpen, MessageSquare, Upload, ArrowRight } from 'lucide-react'
import { useAuthStore } from '@/lib/store'
import { PaperListItem } from '@/types'
import api from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'
import StatusBadge from '@/components/papers/StatusBadge'

export default function DashboardPage() {
  const { user } = useAuthStore()
  const [papers, setPapers] = useState<PaperListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/api/v1/papers/')
      .then(r => setPapers(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const ready = papers.filter(p => p.status === 'ready').length
  const processing = papers.filter(p => p.status === 'processing' || p.status === 'pending').length
  const recent = papers.slice(0, 4)

  return (
    <div className="max-w-3xl mx-auto px-8 py-10">
      <div className="mb-8">
        <h2 className="font-display text-2xl text-navy">
          Welcome back, {user?.name.split(' ')[0]}
        </h2>
        <p className="text-muted text-sm mt-1">
          {papers.length === 0
            ? 'Upload your first paper to get started.'
            : `${ready} paper${ready !== 1 ? 's' : ''} ready to explore.`}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Total papers', value: papers.length, icon: BookOpen, color: 'text-accent' },
          { label: 'Processing', value: processing, icon: Upload, color: 'text-amber-500' },
          { label: 'Ready', value: ready, icon: MessageSquare, color: 'text-green-600' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="border border-parchment-border rounded-xl p-4 bg-parchment/30">
            <div className={`${color} mb-2`}><Icon size={18} /></div>
            <p className="text-2xl font-semibold text-navy">{value}</p>
            <p className="text-xs text-muted mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-3 mb-8">
        <Link href="/papers" className="flex items-center gap-3 p-4 border border-parchment-border rounded-xl hover:shadow-paper transition-shadow bg-white group">
          <div className="w-9 h-9 bg-accent/10 rounded-lg flex items-center justify-center">
            <Upload size={16} className="text-accent" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-navy">Upload paper</p>
            <p className="text-xs text-muted">Add a PDF to your library</p>
          </div>
          <ArrowRight size={14} className="text-muted group-hover:text-accent transition-colors" />
        </Link>

        <Link href="/chat" className="flex items-center gap-3 p-4 border border-parchment-border rounded-xl hover:shadow-paper transition-shadow bg-white group">
          <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center">
            <MessageSquare size={16} className="text-green-600" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-navy">Ask a question</p>
            <p className="text-xs text-muted">Search across all papers</p>
          </div>
          <ArrowRight size={14} className="text-muted group-hover:text-green-600 transition-colors" />
        </Link>
      </div>

      {/* Recent papers */}
      {recent.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-navy">Recent papers</h3>
            <Link href="/papers" className="text-xs text-accent hover:underline">View all</Link>
          </div>
          <div className="space-y-2">
            {recent.map(paper => (
              <Link key={paper.id} href={`/papers/${paper.id}`}
                className="flex items-start gap-3 p-3 border border-parchment-border rounded-lg hover:bg-parchment/30 transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-navy truncate">{paper.title}</p>
                  {paper.summary_short && (
                    <p className="text-xs text-muted mt-0.5 line-clamp-1">{paper.summary_short}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <StatusBadge status={paper.status} />
                  <span className="text-xs text-muted">
                    {formatDistanceToNow(new Date(paper.created_at), { addSuffix: true })}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {papers.length === 0 && !loading && (
        <div className="text-center py-16 border-2 border-dashed border-parchment-border rounded-xl">
          <BookOpen size={32} className="text-parchment-border mx-auto mb-3" />
          <p className="text-navy font-medium">No papers yet</p>
          <p className="text-muted text-sm mt-1 mb-4">Upload a PDF to get started</p>
          <Link href="/papers" className="btn-primary inline-flex">Upload your first paper</Link>
        </div>
      )}
    </div>
  )
}
