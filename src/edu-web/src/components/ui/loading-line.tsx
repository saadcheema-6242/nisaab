/**
 * "Loading X" where a panel has nothing to show yet.
 *
 * There were a dozen of these written out by hand across the app, each a
 * slightly different size, colour and wording, and several with no spinner
 * at all - which on a slow connection is indistinguishable from a panel
 * that has quietly failed.
 *
 * One component instead, so they all say it the same way and all prove the
 * page is still working. Where the shape of the eventual content is known,
 * prefer a skeleton: it does not make the layout jump when the data lands.
 * This is for the cases where it is not.
 */

import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

export const LoadingLine = ({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) => (
  <p
    // Announced once, politely: a screen reader should hear "Loading the
    // class rooms" without it interrupting whatever is being read.
    role="status"
    aria-live="polite"
    className={cn(
      'text-muted-foreground flex items-center justify-center gap-2 py-8 text-sm',
      className,
    )}
  >
    <Spinner className="size-3.5" />
    {children}
  </p>
)
