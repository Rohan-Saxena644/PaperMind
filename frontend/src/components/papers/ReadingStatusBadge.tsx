import { ReadingStatus } from '@/types'
import clsx from 'clsx'

const config: Record<ReadingStatus, { label: string; classes: string }> = {
  unread: { label: 'Unread', classes: 'bg-gray-100 text-gray-600' },
  reading: { label: 'Reading', classes: 'bg-blue-50 text-blue-700' },
  done: { label: 'Done', classes: 'bg-green-50 text-green-700' },
}

export default function ReadingStatusBadge({ status }: { status: ReadingStatus }) {
  const { label, classes } = config[status]
  return (
    <span className={clsx('status-badge', classes)}>
      {label}
    </span>
  )
}
