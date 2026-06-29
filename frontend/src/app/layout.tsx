import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PaperMind — AI Research Workspace',
  description: 'Upload papers, get AI summaries, ask questions across your entire research library.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
