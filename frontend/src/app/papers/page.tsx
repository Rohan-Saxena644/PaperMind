'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Loader2, Link as LinkIcon, Search, Plus } from 'lucide-react'
import { ArxivSearchResult, PaperListItem } from '@/types'
import api from '@/lib/api'
import StatusBadge from '@/components/papers/StatusBadge'
import ReadingStatusBadge from '@/components/papers/ReadingStatusBadge'
import { formatDistanceToNow } from 'date-fns'

export default function PapersPage() {
  const [papers, setPapers] = useState<PaperListItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [ingestingUrl, setIngestingUrl] = useState(false)
  const [sourceUrl, setSourceUrl] = useState('')
  const [arxivQuery, setArxivQuery] = useState('')
  const [arxivResults, setArxivResults] = useState<ArxivSearchResult[]>([])
  const [searchingArxiv, setSearchingArxiv] = useState(false)
  const [importingArxivId, setImportingArxivId] = useState<string | null>(null)
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

  const ingestUrl = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!sourceUrl.trim()) return

    setIngestingUrl(true)
    setUploadError('')
    try {
      await api.post('/api/v1/papers/ingest-url', { url: sourceUrl.trim() })
      setSourceUrl('')
      await fetchPapers()
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'URL ingestion failed.')
    } finally {
      setIngestingUrl(false)
    }
  }

  const searchArxiv = async (e: React.FormEvent) => {
    e.preventDefault()
    if (arxivQuery.trim().length < 2) return

    setSearchingArxiv(true)
    setUploadError('')
    try {
      const { data } = await api.get('/api/v1/papers/arxiv/search', {
        params: { query: arxivQuery.trim(), max_results: 6 },
      })
      setArxivResults(data.results)
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'arXiv search failed.')
    } finally {
      setSearchingArxiv(false)
    }
  }

  const importArxiv = async (paper: ArxivSearchResult) => {
    setImportingArxivId(paper.arxiv_id)
    setUploadError('')
    try {
      await api.post('/api/v1/papers/arxiv/import', {
        pdf_url: paper.pdf_url,
        entry_url: paper.entry_url,
        title: paper.title,
        authors: paper.authors,
        published_year: paper.published_year,
      })
      setArxivResults(prev => prev.filter(item => item.arxiv_id !== paper.arxiv_id))
      await fetchPapers()
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'arXiv import failed.')
    } finally {
      setImportingArxivId(null)
    }
  }

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

      <form onSubmit={ingestUrl} className="border border-parchment-border rounded-xl p-4 mb-6 bg-white">
        <div className="flex items-center gap-2 mb-3">
          <LinkIcon size={16} className="text-accent" />
          <div>
            <p className="text-sm font-medium text-navy">Import from URL</p>
            <p className="text-xs text-muted">Web articles and YouTube videos with transcripts</p>
          </div>
        </div>
        <div className="flex gap-2">
          <input
            className="input"
            type="url"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="https://example.com/article"
            disabled={ingestingUrl}
          />
          <button
            type="submit"
            disabled={ingestingUrl || !sourceUrl.trim()}
            className="btn-primary flex items-center gap-1.5 whitespace-nowrap"
          >
            {ingestingUrl ? <Loader2 size={14} className="animate-spin" /> : <LinkIcon size={14} />}
            Import
          </button>
        </div>
      </form>

      <form onSubmit={searchArxiv} className="border border-parchment-border rounded-xl p-4 mb-6 bg-white">
        <div className="flex items-center gap-2 mb-3">
          <Search size={16} className="text-accent" />
          <div>
            <p className="text-sm font-medium text-navy">Search arXiv</p>
            <p className="text-xs text-muted">Find and import papers without downloading PDFs manually</p>
          </div>
        </div>
        <div className="flex gap-2">
          <input
            className="input"
            value={arxivQuery}
            onChange={(e) => setArxivQuery(e.target.value)}
            placeholder="transformers for time series"
            disabled={searchingArxiv}
          />
          <button
            type="submit"
            disabled={searchingArxiv || arxivQuery.trim().length < 2}
            className="btn-primary flex items-center gap-1.5 whitespace-nowrap"
          >
            {searchingArxiv ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            Search
          </button>
        </div>

        {arxivResults.length > 0 && (
          <div className="mt-4 space-y-2">
            {arxivResults.map(result => (
              <div key={result.arxiv_id} className="border border-parchment-border rounded-lg p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-navy leading-snug">{result.title}</p>
                    <p className="text-xs text-muted mt-0.5 line-clamp-1">
                      {result.published_year ? `${result.published_year} · ` : ''}{result.authors.join(', ')}
                    </p>
                    <p className="text-xs text-muted mt-2 line-clamp-2">{result.summary}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => importArxiv(result)}
                    disabled={importingArxivId === result.arxiv_id}
                    className="btn-secondary inline-flex items-center gap-1.5 text-xs whitespace-nowrap"
                  >
                    {importingArxivId === result.arxiv_id ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <Plus size={13} />
                    )}
                    Import
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </form>

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
              href={paper.status === 'ready' || paper.status === 'failed' ? `/papers/${paper.id}` : '#'}
              className={`block border border-parchment-border rounded-xl p-4 transition-shadow ${
                paper.status === 'ready' || paper.status === 'failed'
                  ? 'hover:shadow-paper cursor-pointer'
                  : 'cursor-default opacity-80'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-navy text-sm leading-snug">{paper.title}</p>
                  {paper.source_type !== 'pdf' && (
                    <p className="text-xs text-accent mt-0.5">
                      {paper.source_type === 'youtube' ? 'YouTube' : paper.source_type === 'arxiv' ? 'arXiv' : 'URL'} source
                    </p>
                  )}
                  {paper.authors && <p className="text-xs text-muted mt-0.5">{paper.authors}</p>}
                  {paper.summary_short && paper.status === 'ready' && (
                    <p className="text-xs text-muted mt-1.5 line-clamp-2">{paper.summary_short}</p>
                  )}
                  {(paper.status === 'pending' || paper.status === 'processing') && (
                    <p className="text-xs text-amber-600 mt-1.5 flex items-center gap-1">
                      <Loader2 size={11} className="animate-spin" />
                      {paper.next_retry_at ? 'Retry scheduled…' : 'AI is processing your paper…'}
                    </p>
                  )}
                  {paper.status === 'failed' && paper.error_message && (
                    <p className="text-xs text-red-600 mt-1.5 line-clamp-2">
                      {paper.error_message}
                    </p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                  <div className="flex items-center gap-1.5">
                    <ReadingStatusBadge status={paper.reading_status} />
                    <StatusBadge status={paper.status} />
                  </div>
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
