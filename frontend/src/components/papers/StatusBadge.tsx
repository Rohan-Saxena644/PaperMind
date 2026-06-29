import { PaperStatus } from '@/types'
import clsx from 'clsx'

const config: Record<PaperStatus, { label: string; classes: string }> = {
  pending:    { label: 'Queued',     classes: 'bg-gray-100 text-gray-600' },
  processing: { label: 'Processing', classes: 'bg-amber-50 text-amber-700' },
  ready:      { label: 'Ready',      classes: 'bg-green-50 text-green-700' },
  failed:     { label: 'Failed',     classes: 'bg-red-50 text-red-600' },
}

export default function StatusBadge({ status }: { status: PaperStatus }) {
  const { label, classes } = config[status]
  return (
    <span className={clsx('status-badge', classes)}>
      {status === 'processing' && (
        <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
      )}
      {label}
    </span>
  )
}
