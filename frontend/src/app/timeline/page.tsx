'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { CalendarDays, Loader2 } from 'lucide-react'
import api from '@/lib/api'
import { TimelineResponse } from '@/types'
import ReadingStatusBadge from '@/components/papers/ReadingStatusBadge'

export default function TimelinePage() {
  const [timeline, setTimeline] = useState<TimelineResponse>({ years: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/api/v1/timeline/')
      .then(r => setTimeline(r.data))
      .catch(err => setError(err.response?.data?.detail || 'Could not load timeline.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-4xl mx-auto px-8 py-10">
      <div className="mb-8">
        <h2 className="font-display text-2xl text-navy">Paper timeline</h2>
        <p className="text-muted text-sm mt-0.5">
          A chronological view of papers and recurring concepts in your library
        </p>
      </div>

      {loading ? (
        <div className="h-64 border border-parchment-border rounded-xl flex items-center justify-center">
          <Loader2 size={22} className="animate-spin text-accent" />
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2">
          {error}
        </div>
      ) : timeline.years.length === 0 ? (
        <div className="text-center py-16 border-2 border-dashed border-parchment-border rounded-xl">
          <CalendarDays size={32} className="text-parchment-border mx-auto mb-3" />
          <p className="text-navy font-medium">No timeline yet</p>
          <p className="text-muted text-sm mt-1">Upload and process papers to build your research timeline.</p>
        </div>
      ) : (
        <div className="relative">
          <div className="absolute left-[75px] top-2 bottom-2 w-px bg-parchment-border" />
          <div className="space-y-8">
            {timeline.years.map(year => (
              <section key={year.year} className="relative grid grid-cols-[110px_1fr] gap-6">
                <div className="relative">
                  <div className="sticky top-8">
                    <div className="inline-flex items-center justify-center w-[76px] h-[38px] rounded-lg bg-navy text-white font-semibold text-sm">
                      {year.year}
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  {year.concepts.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {year.concepts.map(concept => (
                        <span key={concept} className="text-xs bg-accent/8 text-accent px-2 py-0.5 rounded-full border border-accent/20">
                          {concept}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="space-y-2">
                    {year.papers.map(paper => (
                      <Link
                        key={paper.id}
                        href={`/papers/${paper.id}`}
                        className="block border border-parchment-border rounded-xl p-4 hover:shadow-paper transition-shadow bg-white"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-navy leading-snug">{paper.title}</p>
                            {paper.authors && (
                              <p className="text-xs text-muted mt-0.5 line-clamp-1">{paper.authors}</p>
                            )}
                            {paper.summary_short && (
                              <p className="text-xs text-muted mt-2 line-clamp-2">{paper.summary_short}</p>
                            )}
                          </div>
                          <ReadingStatusBadge status={paper.reading_status} />
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              </section>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
