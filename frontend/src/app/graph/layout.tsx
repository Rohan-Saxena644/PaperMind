import AppSidebar from '@/components/layout/AppSidebar'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppSidebar>{children}</AppSidebar>
  )
}
