'use client'

import { useEffect, useState } from 'react'
import { Check, Loader2, Plus } from 'lucide-react'
import api from '@/lib/api'
import { Workspace } from '@/types'

export default function WorkspaceSwitcher() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [activeId, setActiveId] = useState<string>('')
  const [newName, setNewName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function loadWorkspaces() {
      try {
        const { data } = await api.get<Workspace[]>('/api/v1/workspaces/')
        if (cancelled) return

        setWorkspaces(data)
        const storedId = localStorage.getItem('pm_workspace_id')
        const selected = data.find((workspace) => workspace.id === storedId) || data.find((workspace) => workspace.is_default) || data[0]

        if (selected) {
          localStorage.setItem('pm_workspace_id', selected.id)
          setActiveId(selected.id)
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    loadWorkspaces()
    return () => {
      cancelled = true
    }
  }, [])

  const selectWorkspace = (workspaceId: string) => {
    if (!workspaceId || workspaceId === activeId) return
    localStorage.setItem('pm_workspace_id', workspaceId)
    setActiveId(workspaceId)
    window.location.reload()
  }

  const createWorkspace = async () => {
    const name = newName.trim()
    if (!name || isCreating) return

    setIsCreating(true)
    try {
      const { data } = await api.post<Workspace>('/api/v1/workspaces/', { name })
      localStorage.setItem('pm_workspace_id', data.id)
      setWorkspaces((prev) => [...prev, data])
      setActiveId(data.id)
      setNewName('')
      window.location.reload()
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-2">
        <select
          value={activeId}
          onChange={(event) => selectWorkspace(event.target.value)}
          disabled={isLoading}
          className="min-w-0 flex-1 rounded-lg border border-parchment-border bg-white px-2 py-2 text-xs text-navy outline-none focus:border-accent"
          aria-label="Workspace"
        >
          {isLoading ? (
            <option>Loading...</option>
          ) : (
            workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>
                {workspace.name}
              </option>
            ))
          )}
        </select>
      </div>

      <div className="flex items-center gap-1.5">
        <input
          value={newName}
          onChange={(event) => setNewName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') createWorkspace()
          }}
          placeholder="New workspace"
          className="min-w-0 flex-1 rounded-lg border border-parchment-border bg-white px-2 py-1.5 text-xs text-navy outline-none placeholder:text-muted focus:border-accent"
        />
        <button
          type="button"
          onClick={createWorkspace}
          disabled={!newName.trim() || isCreating}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-accent text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Create workspace"
          title="Create workspace"
        >
          {isCreating ? <Loader2 size={14} className="animate-spin" /> : activeId ? <Plus size={14} /> : <Check size={14} />}
        </button>
      </div>
    </div>
  )
}
