'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import { useAuthStore } from '@/lib/store'

export default function OAuthCallbackPage() {
  const router = useRouter()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [error, setError] = useState('')

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search)
    const token = searchParams.get('token')
    if (!token) {
      setError('OAuth login did not return a session token.')
      return
    }

    const finishLogin = async () => {
      try {
        localStorage.setItem('pm_token', token)
        const { data: user } = await api.get('/api/v1/auth/me')
        localStorage.setItem('pm_user', JSON.stringify(user))
        setAuth(token, user)
        router.replace('/dashboard')
      } catch {
        localStorage.removeItem('pm_token')
        localStorage.removeItem('pm_user')
        setError('Could not finish OAuth login. Please try again.')
      }
    }

    finishLogin()
  }, [router, setAuth])

  return (
    <div className="min-h-screen bg-parchment flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-xl border border-parchment-border p-6 text-center">
        <h1 className="font-display text-2xl text-navy mb-2">PaperMind</h1>
        <p className="text-sm text-muted">
          {error || 'Finishing sign in...'}
        </p>
      </div>
    </div>
  )
}
