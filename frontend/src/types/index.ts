export type PaperStatus = 'pending' | 'processing' | 'ready' | 'failed'

export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

export interface Paper {
  id: string
  title: string
  authors: string | null
  abstract: string | null
  file_name: string
  file_size: number
  status: PaperStatus
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
  title: string
  authors: string | null
  status: PaperStatus
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
  question: string
  answer: string
  paper_id: string
  paper_title: string
}
