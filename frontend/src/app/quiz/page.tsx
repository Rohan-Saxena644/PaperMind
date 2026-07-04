'use client'

import { useState } from 'react'
import { Brain, Loader2, ArrowRight, RotateCcw, Eye, Clock } from 'lucide-react'
import { QuizQuestion } from '@/types'
import api from '@/lib/api'

type QuizState = 'idle' | 'active' | 'finished'

export default function QuizPage() {
  const [state, setState] = useState<QuizState>('idle')
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [current, setCurrent] = useState(0)
  const [showAnswer, setShowAnswer] = useState(false)
  const [knownCount, setKnownCount] = useState(0)
  const [unknownCount, setUnknownCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [grading, setGrading] = useState(false)
  const [error, setError] = useState('')

  const startQuiz = async () => {
    setLoading(true)
    setError('')
    try {
      const r = await api.get('/api/v1/papers/quiz/random?count=10')
      setQuestions(r.data.questions)
      setCurrent(0)
      setKnownCount(0)
      setUnknownCount(0)
      setShowAnswer(false)
      setState('active')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not start quiz.')
    } finally {
      setLoading(false)
    }
  }

  const markAndNext = async (quality: number) => {
    if (!q || grading) return

    setGrading(true)
    setError('')
    try {
      await api.post('/api/v1/papers/quiz/review', {
        card_key: q.card_key,
        paper_id: q.paper_id,
        question: q.question,
        answer: q.answer,
        quality,
      })

      if (quality >= 3) setKnownCount(c => c + 1)
      else setUnknownCount(c => c + 1)

      if (current + 1 >= questions.length) {
        setState('finished')
      } else {
        setCurrent(c => c + 1)
        setShowAnswer(false)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not save this review.')
    } finally {
      setGrading(false)
    }
  }

  const restart = () => setState('idle')

  const q = questions[current]
  const isDue = q ? new Date(q.due_at).getTime() <= Date.now() : false

  return (
    <div className="max-w-2xl mx-auto px-8 py-10">
      <div className="mb-6">
        <h2 className="font-display text-2xl text-navy flex items-center gap-2">
          <Brain size={22} className="text-accent" /> Quiz mode
        </h2>
          <p className="text-muted text-sm mt-1">Review due flashcards first, then keep practicing across your library.</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2 mb-6">
          {error}
        </div>
      )}

      {state === 'idle' && (
        <div className="text-center py-16 border-2 border-dashed border-parchment-border rounded-xl">
          <Brain size={32} className="text-parchment-border mx-auto mb-3" />
          <p className="text-navy font-medium">Ready to test your knowledge?</p>
          <p className="text-muted text-sm mt-1 mb-5">10 scheduled review cards from across all your papers</p>
          <button onClick={startQuiz} disabled={loading} className="btn-primary inline-flex items-center gap-2">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Brain size={14} />}
            {loading ? 'Loading…' : 'Start quiz'}
          </button>
        </div>
      )}

      {state === 'active' && q && (
        <div>
          {/* Progress */}
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs text-muted">Question {current + 1} of {questions.length}</span>
            <span className="text-xs text-muted text-right">{q.paper_title}</span>
          </div>
          <div className="w-full h-1.5 bg-parchment rounded-full mb-6 overflow-hidden">
            <div
              className="h-full bg-accent transition-all duration-300"
              style={{ width: `${((current) / questions.length) * 100}%` }}
            />
          </div>

          {/* Card */}
          <div className="border border-parchment-border rounded-2xl p-8 min-h-[220px] flex flex-col">
            <div className="flex items-center justify-between gap-3 mb-3">
              <span className="text-xs font-mono text-accent">QUESTION</span>
              <span className="text-xs text-muted inline-flex items-center gap-1">
                <Clock size={12} /> {isDue ? 'Due now' : `${q.repetitions} reviews`}
              </span>
            </div>
            <p className="text-lg text-navy font-medium leading-relaxed flex-1">{q.question}</p>

            {showAnswer && (
              <div className="mt-4 pt-4 border-t border-parchment-border">
                <span className="text-xs font-mono text-green-600 mb-2 block">ANSWER</span>
                <p className="text-sm text-navy/80 leading-relaxed">{q.answer}</p>
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="mt-5">
            {!showAnswer ? (
              <button
                onClick={() => setShowAnswer(true)}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <Eye size={14} /> Reveal answer
              </button>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <button
                  onClick={() => markAndNext(1)}
                  disabled={grading}
                  className="px-4 py-2.5 rounded-lg border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 transition-colors"
                >
                  Again
                </button>
                <button
                  onClick={() => markAndNext(3)}
                  disabled={grading}
                  className="px-4 py-2.5 rounded-lg border border-amber-200 text-amber-700 text-sm font-medium hover:bg-amber-50 transition-colors"
                >
                  Hard
                </button>
                <button
                  onClick={() => markAndNext(4)}
                  disabled={grading}
                  className="px-4 py-2.5 rounded-lg border border-green-200 text-green-700 text-sm font-medium hover:bg-green-50 transition-colors"
                >
                  Good
                </button>
                <button
                  onClick={() => markAndNext(5)}
                  disabled={grading}
                  className="px-4 py-2.5 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors flex items-center justify-center gap-1.5"
                >
                  Easy {grading ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {state === 'finished' && (
        <div className="text-center py-12">
          <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Brain size={28} className="text-accent" />
          </div>
          <h3 className="font-display text-xl text-navy mb-1">Quiz complete</h3>
          <p className="text-muted text-sm mb-6">
            You passed {knownCount} of {questions.length} cards ({Math.round((knownCount / questions.length) * 100)}%)
          </p>

          <div className="flex items-center justify-center gap-6 mb-8">
            <div>
              <p className="text-2xl font-semibold text-green-600">{knownCount}</p>
              <p className="text-xs text-muted">Scheduled forward</p>
            </div>
            <div className="w-px h-10 bg-parchment-border" />
            <div>
              <p className="text-2xl font-semibold text-red-500">{unknownCount}</p>
              <p className="text-xs text-muted">Repeat soon</p>
            </div>
          </div>

          <button onClick={restart} className="btn-primary inline-flex items-center gap-2">
            <RotateCcw size={14} /> Take another quiz
          </button>
        </div>
      )}
    </div>
  )
}
