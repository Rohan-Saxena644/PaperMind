export type PaperStatus = 'pending' | 'processing' | 'ready' | 'failed'
export type ReadingStatus = 'unread' | 'reading' | 'done'
export type PaperSource = 'pdf' | 'url' | 'youtube' | 'arxiv'

export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

export interface Workspace {
  id: string
  name: string
  description: string | null
  is_default: boolean
  created_at: string
}

export interface Paper {
  id: string
  workspace_id: string | null
  title: string
  authors: string | null
  abstract: string | null
  publication_year: number | null
  file_name: string
  file_size: number
  source_type: PaperSource
  source_url: string | null
  status: PaperStatus
  error_message: string | null
  processing_attempts: number
  next_retry_at: string | null
  failed_at: string | null
  reading_status: ReadingStatus
  personal_notes: string | null
  highlights: string[] | null
  summary_short: string | null
  summary_long: string | null
  key_contributions: string[] | null
  keywords: string[] | null
  flashcards: Flashcard[] | null
  total_chunks: number
  created_at: string
  processed_at: string | null
}

export interface PaperListItem {
  id: string
  workspace_id: string | null
  title: string
  authors: string | null
  publication_year: number | null
  source_type: PaperSource
  source_url: string | null
  status: PaperStatus
  error_message: string | null
  processing_attempts: number
  next_retry_at: string | null
  reading_status: ReadingStatus
  summary_short: string | null
  total_chunks: number
  created_at: string
}

export interface Flashcard {
  question: string
  answer: string
}

export interface MessageSource {
  paper_id: string
  paper_title: string
  chunk_content: string
  score: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources: MessageSource[] | null
  created_at: string
}

export interface Chat {
  id: string
  workspace_id: string | null
  title: string
  created_at: string
  messages: Message[]
}

export interface ComparisonRow {
  aspect: string
  values: string[]
}

export interface Comparison {
  overview: string
  similarities: string[]
  differences: string[]
  comparison_table: ComparisonRow[]
  recommendation: string
  paper_titles: string[]
}

export interface QuizQuestion {
  card_key: string
  question: string
  answer: string
  paper_id: string
  paper_title: string
  due_at: string
  repetitions: number
  ease_factor: number
}

export interface GraphNode {
  id: string
  type: 'paper' | 'concept' | 'author' | string
  label: string
  x: number
  y: number
  centrality: number
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
}

export interface KnowledgeGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphInsightConcept {
  id: string
  label: string
  centrality: number
}

export interface GraphInsights {
  node_count: number
  edge_count: number
  paper_count: number
  concept_count: number
  author_count: number
  research_thread_count: number
  density: number
  top_concepts: GraphInsightConcept[]
}

export interface TimelinePaper {
  id: string
  title: string
  authors: string | null
  summary_short: string | null
  keywords: string[]
  reading_status: ReadingStatus
  publication_year: number | null
  created_at: string
}

export interface TimelineYear {
  year: number
  papers: TimelinePaper[]
  concepts: string[]
}

export interface TimelineResponse {
  years: TimelineYear[]
}

export interface ArxivSearchResult {
  arxiv_id: string
  title: string
  authors: string[]
  summary: string
  published_year: number | null
  pdf_url: string
  entry_url: string
}
