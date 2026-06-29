'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Loader2 } from 'lucide-react'
import { PaperListItem } from '@/types'
import api from '@/lib/api'
import StatusBadge from '@/components/papers/StatusBadge'
import { formatDistanceToNow } from 'date-fns'

export default function PapersPage() {
  const [papers, setPapers] = useState<PaperListItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')

  const fetchPapers = () =>
    api.get('/api/v1/papers/').then(r => setPapers(r.data)).catch(console.error)

  useEffect(() => {
    fetchPapers()
    // Poll every 5s while any paper is still processing
    const interval = setInterval(() => {
      const anyProcessing = papers.some(p => p.status === 'pending' || p.status === 'processing')
      if (anyProcessing) fetchPapers()
    }, 5000)
    return () => clearInterval(interval)
  }, [papers])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploading(true)
    setUploadError('')

    const form = new FormData()
    form.append('file', file)

    try {
      await api.post('/api/v1/papers/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await fetchPapers()
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: uploading,
  })

  return (
    <div className="max-w-3xl mx-auto px-8 py-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-display text-2xl text-navy">Papers</h2>
          <p className="text-muted text-sm mt-0.5">{papers.length} paper{papers.length !== 1 ? 's' : ''} in your library</p>
        </div>
      </div>

      {/* Upload zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors mb-6 ${
          isDragActive ? 'border-accent bg-accent/5' : 'border-parchment-border hover:border-accent/50 hover:bg-parchment/30'
        } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 size={24} className="text-accent animate-spin" />
            <p className="text-sm text-muted">Uploading and queuing for processing…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload size={24} className={isDragActive ? 'text-accent' : 'text-muted'} />
            <p className="text-sm font-medium text-navy">
              {isDragActive ? 'Drop to upload' : 'Drop a PDF here, or click to browse'}
            </p>
            <p className="text-xs text-muted">PDF only · Max 50MB</p>
          </div>
        )}
      </div>

      {uploadError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2">
          {uploadError}
        </div>
      )}

      {/* Papers list */}
      {papers.length === 0 ? (
        <div className="text-center py-12 text-muted">
          <FileText size={28} className="mx-auto mb-2 text-parchment-border" />
          <p className="text-sm">No papers yet. Upload one above.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {papers.map(paper => (
            <Link
              key={paper.id}
              href={paper.status === 'ready' ? `/papers/${paper.id}` : '#'}
              className={`block border border-parchment-border rounded-xl p-4 transition-shadow ${
                paper.status === 'ready' ? 'hover:shadow-paper cursor-pointer' : 'cursor-default opacity-80'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-navy text-sm leading-snug">{paper.title}</p>
                  {paper.authors && <p className="text-xs text-muted mt-0.5">{paper.authors}</p>}
                  {paper.summary_short && paper.status === 'ready' && (
                    <p className="text-xs text-muted mt-1.5 line-clamp-2">{paper.summary_short}</p>
                  )}
                  {(paper.status === 'pending' || paper.status === 'processing') && (
                    <p className="text-xs text-amber-600 mt-1.5 flex items-center gap-1">
                      <Loader2 size={11} className="animate-spin" />
                      AI is processing your paper…
                    </p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                  <StatusBadge status={paper.status} />
                  <span className="text-xs text-muted">
                    {formatDistanceToNow(new Date(paper.created_at), { addSuffix: true })}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
