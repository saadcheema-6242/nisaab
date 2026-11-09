/**
 * The title block at the top of a main screen.
 *
 * Weekly sessions, Progress, Accounts and the community room each wrote
 * this out themselves, identically, which is how four screens end up with
 * four slightly different headers once one of them is touched.
 *
 * The icon moves out of the heading and into a tinted tile beside it. In
 * the old markup it was a child of the h1, so it was part of the accessible
 * name of the page - a screen reader got the icon's box as part of the
 * title - and visually it sat on the text baseline, which at 30px serif
 * left it looking dropped. In a tile it is an object next to the title
 * instead of a letter in it.
 */

import { cn } from '@/lib/utils'

export const PageHeader = ({
  icon: Icon,
  title,
  children,
  action,
  className,
}: {
  /** A lucide icon component, e.g. CalendarDaysIcon. */
  icon?: React.ComponentType<{ className?: string }>
  title: React.ReactNode
  /** The line or two under the title. */
  children?: React.ReactNode
  /** A control belonging to the whole page, right-aligned. */
  action?: React.ReactNode
  className?: string
}) => (
  <header className={cn('flex flex-wrap items-start gap-4', className)}>
    {Icon && (
      <div
        aria-hidden
        className="bg-accent text-accent-foreground ring-accent-foreground/10 grid size-11 shrink-0 place-items-center rounded-xl ring-1"
      >
        <Icon className="size-5" />
      </div>
    )}
    <div className="min-w-0 flex-1 space-y-1.5">
      {/* h1, so it takes the serif and the tracking from the global sheet. */}
      <h1 className="text-2xl font-semibold sm:text-3xl">{title}</h1>
      {children && (
        <div className="text-muted-foreground max-w-2xl text-sm leading-relaxed">
          {children}
        </div>
      )}
    </div>
    {action}
  </header>
)
