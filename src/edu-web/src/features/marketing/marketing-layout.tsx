import { Link } from '@tanstack/react-router'
import { MenuIcon, XIcon } from 'lucide-react'
import { useState } from 'react'
import { college, nav, supervisor } from './site-data'
import type { ReactNode } from 'react'
import { NisaabMark } from '@/components/nisaab-mark'
import { Button } from '@/components/ui/button'
import { brand } from '@/lib/brand'
import { cn } from '@/lib/utils'

const Wordmark = () => (
  <Link to="/" className="flex items-center gap-2.5">
    <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-lg">
      <NisaabMark className="size-5" />
    </span>
    <span className="text-lg font-bold tracking-tight">{brand.name}</span>
  </Link>
)

const NavLinks = ({ onNavigate }: { onNavigate?: () => void }) => (
  <>
    {nav.map((item) => (
      <Link
        key={item.to}
        to={item.to}
        onClick={onNavigate}
        className="text-muted-foreground hover:text-foreground text-sm font-medium transition-colors"
        activeProps={{ className: 'text-foreground' }}
        activeOptions={{ exact: item.to === '/' }}
      >
        {item.label}
      </Link>
    ))}
  </>
)

export const MarketingLayout = ({ children }: { children: ReactNode }) => {
  const [open, setOpen] = useState(false)

  return (
    <div className="bg-background flex min-h-screen flex-col">
      <header className="bg-background/80 sticky top-0 z-50 border-b backdrop-blur-md">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <Wordmark />

          <nav className="hidden items-center gap-8 md:flex">
            <NavLinks />
          </nav>

          <div className="hidden items-center gap-2 md:flex">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/sign-in">Sign in</Link>
            </Button>
            <Button size="sm" asChild>
              <Link to="/sign-up">Start free</Link>
            </Button>
          </div>

          <button
            type="button"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            onClick={() => setOpen(!open)}
            className="hover:bg-accent -mr-2 rounded-md p-2 md:hidden"
          >
            {open ? <XIcon className="size-5" /> : <MenuIcon className="size-5" />}
          </button>
        </div>

        <div
          className={cn(
            'grid overflow-hidden border-t transition-all duration-200 md:hidden',
            open ? 'grid-rows-[1fr] border-border' : 'grid-rows-[0fr] border-transparent',
          )}
        >
          <div className="min-h-0">
            <div className="flex flex-col gap-4 px-4 py-5 sm:px-6">
              <NavLinks onNavigate={() => setOpen(false)} />
              <div className="flex gap-2 pt-1">
                <Button variant="outline" size="sm" className="flex-1" asChild>
                  <Link to="/sign-in" onClick={() => setOpen(false)}>
                    Sign in
                  </Link>
                </Button>
                <Button size="sm" className="flex-1" asChild>
                  <Link to="/sign-up" onClick={() => setOpen(false)}>
                    Start free
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t">
        <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
          <div className="flex flex-col gap-10 sm:flex-row sm:justify-between">
            <div className="max-w-xs space-y-3">
              <Wordmark />
              <p className="text-muted-foreground text-sm">{brand.tagline}</p>
            </div>

            <div className="flex gap-16">
              <div className="space-y-3">
                <div className="text-sm font-semibold">Site</div>
                <div className="flex flex-col gap-2.5">
                  <NavLinks />
                </div>
              </div>
              <div className="space-y-3">
                <div className="text-sm font-semibold">Project</div>
                <div className="text-muted-foreground flex flex-col gap-2.5 text-sm">
                  <span>{college}</span>
                  <span>Supervised by {supervisor}</span>
                </div>
              </div>
            </div>
          </div>

          <p className="text-muted-foreground mt-10 border-t pt-6 text-xs">
            {brand.notice}
          </p>
        </div>
      </footer>
    </div>
  )
}
