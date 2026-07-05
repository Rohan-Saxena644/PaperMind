import { create } from 'zustand'
import { User } from '@/types'
import api from '@/lib/api'

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
  init: () => void
  setAuth: (token: string, user: User) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: false,

  init: () => {
    if (typeof window === 'undefined') return
    const token = localStorage.getItem('pm_token')
    const userStr = localStorage.getItem('pm_user')
    if (token && userStr) {
      set({ token, user: JSON.parse(userStr) })
    }
  },

  setAuth: (token, user) => {
    set({ token, user })
  },

  login: async (email, password) => {
    set({ isLoading: true })
    try {
      const { data } = await api.post('/api/v1/auth/login', { email, password })
      localStorage.setItem('pm_token', data.access_token)
      localStorage.setItem('pm_user', JSON.stringify(data.user))
      set({ token: data.access_token, user: data.user })
    } finally {
      set({ isLoading: false })
    }
  },

  register: async (name, email, password) => {
    set({ isLoading: true })
    try {
      const { data } = await api.post('/api/v1/auth/register', { name, email, password })
      localStorage.setItem('pm_token', data.access_token)
      localStorage.setItem('pm_user', JSON.stringify(data.user))
      set({ token: data.access_token, user: data.user })
    } finally {
      set({ isLoading: false })
    }
  },

  logout: () => {
    localStorage.removeItem('pm_token')
    localStorage.removeItem('pm_user')
    localStorage.removeItem('pm_workspace_id')
    set({ user: null, token: null })
    window.location.href = '/auth/login'
  },
}))
