'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { BookOpen, MessageSquare, LayoutDashboard, LogOut, GitCompare, Brain, Network, CalendarDays } from 'lucide-react'
import { useAuthStore } from '@/lib/store'
import clsx from 'clsx'

const navItems = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/papers', label: 'Papers', icon: BookOpen },
  { href: '/chat', label: 'Ask AI', icon: MessageSquare },
  { href: '/compare', label: 'Compare', icon: GitCompare },
  { href: '/quiz', label: 'Quiz', icon: Brain },
  { href: '/graph', label: 'Graph', icon: Network },
  { href: '/timeline', label: 'Timeline', icon: CalendarDays },
]

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, token, logout, init } = useAuthStore()

  useEffect(() => {
    init()
  }, [init])

  useEffect(() => {
    if (!token && !localStorage.getItem('pm_token')) {
      router.push('/auth/login')
    }
  }, [token, router])

  if (!user) return null

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-56 flex-shrink-0 bg-parchment border-r border-parchment-border flex flex-col">
        <div className="px-5 py-5 border-b border-parchment-border">
          <h1 className="font-display text-xl text-navy">PaperMind</h1>
          <p className="text-xs text-muted mt-0.5 truncate">{user.name}</p>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                pathname === href || pathname.startsWith(href + '/')
                  ? 'bg-white text-navy font-medium shadow-sm border border-parchment-border'
                  : 'text-muted hover:text-navy hover:bg-white/60'
              )}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-parchment-border">
          <button
            onClick={logout}
            className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm text-muted hover:text-navy hover:bg-white/60 transition-colors"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-white">
        {children}
      </main>
    </div>
  )
}
