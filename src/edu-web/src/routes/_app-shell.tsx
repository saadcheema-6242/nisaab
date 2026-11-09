import { Outlet, useLocation } from '@tanstack/react-router'
import { useAtomValue } from '@effect-atom/atom-react'
import { AppSidebar } from '@/components/navigation/app-sidebar'
import { ThemeToggle } from '@/components/theme-toggle'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { isAuthenticatedAtom } from '@/data-acess/auth'

export const AppShell = () => {
  const isAuthenticated = useAtomValue(isAuthenticatedAtom)

  const location = useLocation()

  // Only show sidebar on dashboard routes
  const isDashboardRoute = location.pathname.startsWith('/dashboard')

  if (!isAuthenticated || !isDashboardRoute) {
    return <Outlet />
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        {/* A slim bar rather than a full header: the pages carry their own
            titles, so this only holds the two controls that belong to the
            app rather than to any page.

            The sidebar trigger had been commented out, which left no way
            to open the sidebar on a phone, where it is collapsed by
            default. That was a real hole, not only a tidy-up. */}
        <header className="border-border/60 bg-background/80 sticky top-0 z-20 flex h-12 shrink-0 items-center gap-1 border-b px-2 backdrop-blur print:hidden">
          <SidebarTrigger className="text-muted-foreground hover:text-foreground" />
          <div className="flex-1" />
          <ThemeToggle />
        </header>
        <div className="min-h-0 flex-1 overflow-auto">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
