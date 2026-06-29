'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { Send, Plus, MessageSquare, Loader2, BookOpen } from 'lucide-react'
import { Chat, Message } from '@/types'
import api from '@/lib/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

export default function ChatPage() {
  const searchParams = useSearchParams()
  const paperIdFromRoute = searchParams.get('paper')

  const [chats, setChats] = useState<Chat[]>([])
  const [activeChat, setActiveChat] = useState<Chat | null>(null)
  const [question, setQuestion] = useState('')
  const [sending, setSending] = useState(false)
  const [creatingChat, setCreatingChat] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })

  const fetchChats = useCallback(async () => {
    const r = await api.get('/api/v1/chats/')
    setChats(r.data)
    return r.data as Chat[]
  }, [])

  useEffect(() => {
    fetchChats().then(async (fetched) => {
      // If arriving from a paper page, open or create a relevant chat
      if (fetched.length > 0 && !activeChat) {
        const full = await api.get(`/api/v1/chats/${fetched[0].id}`)
        setActiveChat(full.data)
      }
    })
  }, [])

  useEffect(() => { scrollToBottom() }, [activeChat?.messages])

  const createChat = async () => {
    setCreatingChat(true)
    try {
      const r = await api.post('/api/v1/chats/', { title: 'New chat' })
      const newChat: Chat = { ...r.data, messages: [] }
      setChats(prev => [newChat, ...prev])
      setActiveChat(newChat)
    } finally {
      setCreatingChat(false)
    }
  }

  const openChat = async (chatId: string) => {
    const r = await api.get(`/api/v1/chats/${chatId}`)
    setActiveChat(r.data)
  }

  const sendQuestion = async () => {
    if (!question.trim() || !activeChat || sending) return

    const q = question.trim()
    setQuestion('')
    setSending(true)

    // Optimistically add user message
    const tempUserMsg: Message = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: q,
      sources: null,
      created_at: new Date().toISOString(),
    }
    setActiveChat(prev => prev ? { ...prev, messages: [...prev.messages, tempUserMsg] } : prev)

    try {
      const r = await api.post(`/api/v1/chats/${activeChat.id}/ask`, {
        question: q,
        paper_ids: paperIdFromRoute ? [paperIdFromRoute] : null,
      })
      // Replace optimistic message + add assistant response
      setActiveChat(prev => {
        if (!prev) return prev
        const filtered = prev.messages.filter(m => m.id !== tempUserMsg.id)
        return { ...prev, messages: [...filtered, tempUserMsg, r.data] }
      })
      // Update chat title after first message
      if (activeChat.messages.length === 0) {
        const updated = { ...activeChat, title: q.slice(0, 40) + (q.length > 40 ? '…' : '') }
        setChats(prev => prev.map(c => c.id === activeChat.id ? updated : c))
      }
    } catch {
      setActiveChat(prev => {
        if (!prev) return prev
        return { ...prev, messages: prev.messages.filter(m => m.id !== tempUserMsg.id) }
      })
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendQuestion()
    }
  }

  return (
    <div className="flex h-full">
      {/* Chat sidebar */}
      <div className="w-52 flex-shrink-0 border-r border-parchment-border bg-parchment/40 flex flex-col">
        <div className="p-3 border-b border-parchment-border">
          <button
            onClick={createChat}
            disabled={creatingChat}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm font-medium text-white bg-accent hover:bg-accent-hover rounded-lg transition-colors disabled:opacity-50"
          >
            {creatingChat ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            New chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {chats.length === 0 ? (
            <p className="text-xs text-muted text-center py-4 px-2">No chats yet. Start one above.</p>
          ) : (
            chats.map(chat => (
              <button
                key={chat.id}
                onClick={() => openChat(chat.id)}
                className={clsx(
                  'w-full text-left px-3 py-2 rounded-lg text-xs transition-colors',
                  activeChat?.id === chat.id
                    ? 'bg-white text-navy font-medium shadow-sm border border-parchment-border'
                    : 'text-muted hover:text-navy hover:bg-white/60'
                )}
              >
                <p className="truncate">{chat.title}</p>
                <p className="text-muted/60 mt-0.5">
                  {formatDistanceToNow(new Date(chat.created_at), { addSuffix: true })}
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {activeChat ? (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
              {activeChat.messages.length === 0 && (
                <div className="text-center py-16">
                  <MessageSquare size={28} className="text-parchment-border mx-auto mb-3" />
                  <p className="text-navy font-medium text-sm">Ask anything about your papers</p>
                  <p className="text-muted text-xs mt-1">
                    Try: "Explain the attention mechanism" or "Compare the main approaches"
                  </p>
                </div>
              )}

              {activeChat.messages.map((msg) => (
                <div key={msg.id} className={clsx('flex gap-3', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
                  {msg.role === 'assistant' && (
                    <div className="w-7 h-7 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <BookOpen size={13} className="text-accent" />
                    </div>
                  )}

                  <div className={clsx(
                    'max-w-xl rounded-2xl px-4 py-3',
                    msg.role === 'user'
                      ? 'bg-accent text-white rounded-tr-sm'
                      : 'bg-parchment/60 border border-parchment-border text-navy rounded-tl-sm'
                  )}>
                    {msg.role === 'assistant' ? (
                      <div className="prose prose-sm max-w-none prose-headings:text-navy prose-p:text-navy/80">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-sm">{msg.content}</p>
                    )}

                    {/* Sources */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-parchment-border/50 space-y-1.5">
                        <p className="text-xs text-muted font-medium">Sources</p>
                        {msg.sources.map((src, i) => (
                          <div key={i} className="text-xs bg-white/60 rounded-lg px-2 py-1.5 border border-parchment-border">
                            <p className="font-medium text-navy truncate">{src.paper_title}</p>
                            <p className="text-muted mt-0.5 line-clamp-2">{src.chunk_content}</p>
                            <p className="text-accent/70 mt-0.5">score: {src.score.toFixed(3)}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {sending && (
                <div className="flex gap-3 justify-start">
                  <div className="w-7 h-7 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0">
                    <BookOpen size={13} className="text-accent" />
                  </div>
                  <div className="bg-parchment/60 border border-parchment-border rounded-2xl rounded-tl-sm px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce [animation-delay:0ms]" />
                      <span className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce [animation-delay:150ms]" />
                      <span className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-parchment-border p-4">
              {paperIdFromRoute && (
                <p className="text-xs text-muted mb-2 flex items-center gap-1">
                  <BookOpen size={11} /> Searching within selected paper only
                </p>
              )}
              <div className="flex gap-2 items-end">
                <textarea
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about your papers… (Enter to send)"
                  rows={1}
                  className="input flex-1 resize-none min-h-[40px] max-h-32 py-2.5"
                  style={{ height: 'auto' }}
                  onInput={e => {
                    const t = e.target as HTMLTextAreaElement
                    t.style.height = 'auto'
                    t.style.height = t.scrollHeight + 'px'
                  }}
                />
                <button
                  onClick={sendQuestion}
                  disabled={!question.trim() || sending}
                  className="btn-primary p-2.5 flex-shrink-0"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-center px-8">
            <div>
              <MessageSquare size={32} className="text-parchment-border mx-auto mb-3" />
              <p className="text-navy font-medium">No chat selected</p>
              <p className="text-muted text-sm mt-1 mb-4">Create a new chat to start asking questions</p>
              <button onClick={createChat} className="btn-primary">
                Start a new chat
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
