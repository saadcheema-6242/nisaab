/**
 * A row of tabs over panels that stay mounted once opened.
 *
 * Extracted from the Progress page, which had this inline, because the admin
 * dashboard needs exactly the same behaviour and a second copy of it would
 * drift. Two things it does that a pair of styled buttons does not:
 *
 * A real tablist, so arrow keys move between tabs and a screen reader says
 * which of them is showing. Buttons that merely look like tabs announce
 * nothing and trap keyboard users.
 *
 * A panel is mounted the first time its tab is opened and kept thereafter.
 * Mounting everything up front makes the page pay for queries nobody asked
 * for; unmounting on the way out means paying again on every switch.
 */

import { useCallback, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

export type TabDef<TId extends string> = {
  id: TId
  label: string
  /** Shown as a title attribute, so the tab can say what is behind it. */
  hint?: string
  /** A count beside the label, e.g. pending approvals waiting. */
  badge?: number
}

export const useFirstOpened = <TId extends string>(active: TId) => {
  const [opened, setOpened] = useState<Set<TId>>(() => new Set([active]))
  useEffect(() => {
    setOpened((seen) => (seen.has(active) ? seen : new Set(seen).add(active)))
  }, [active])
  return opened
}

export const TabStrip = <TId extends string>({
  tabs,
  active,
  onSelect,
  label,
}: {
  tabs: Array<TabDef<TId>>
  active: TId
  onSelect: (id: TId) => void
  /** What this set of tabs is for, announced to a screen reader. */
  label: string
}) => {
  // Left and right move between tabs, Home and End jump to the ends. This is
  // what the tablist role promises a keyboard user, and without it the role
  // is a lie.
  const onKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      const at = tabs.findIndex((t) => t.id === active)
      if (at < 0) return
      const go =
        event.key === 'ArrowRight'
          ? (at + 1) % tabs.length
          : event.key === 'ArrowLeft'
            ? (at - 1 + tabs.length) % tabs.length
            : event.key === 'Home'
              ? 0
              : event.key === 'End'
                ? tabs.length - 1
                : null
      if (go === null) return
      event.preventDefault()
      onSelect(tabs[go].id)
      document.getElementById(`tab-${tabs[go].id}`)?.focus()
    },
    [tabs, active, onSelect],
  )

  return (
    <div
      role="tablist"
      aria-label={label}
      onKeyDown={onKeyDown}
      className="border-border/70 flex flex-wrap gap-1 border-b"
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          type="button"
          id={`tab-${tab.id}`}
          aria-selected={active === tab.id}
          aria-controls={`panel-${tab.id}`}
          // Only the selected tab is in the tab order; the arrow keys move
          // between them from there. Otherwise a keyboard user has to tab
          // through every one to reach the content.
          tabIndex={active === tab.id ? 0 : -1}
          title={tab.hint}
          onClick={() => onSelect(tab.id)}
          className={cn(
            '-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2.5',
            'text-sm font-medium',
            'transition-[color,border-color,background-color] duration-150 ease-out',
            // The focus ring is inset and square-topped so it cannot be
            // mistaken for the selected-tab underline.
            'rounded-t-md outline-none focus-visible:ring-ring/45 focus-visible:ring-2 focus-visible:ring-inset',
            active === tab.id
              ? 'border-primary text-foreground'
              : [
                  'border-transparent text-muted-foreground',
                  // The unselected tab warms slightly before it commits to
                  // the underline, so the row feels answerable rather than
                  // inert. Only the colour moves; moving the border on hover
                  // would make it look selected.
                  'hover:bg-muted/50 hover:text-foreground',
                ],
          )}
        >
          {tab.label}
          {tab.badge !== undefined && tab.badge > 0 && (
            <span
              className={cn(
                'inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5',
                'text-xs font-semibold tabular-nums',
                active === tab.id
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground',
              )}
            >
              {tab.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

export const TabPanel = ({
  id,
  active,
  opened,
  children,
}: {
  id: string
  active: boolean
  /** False until the tab has been opened once; the panel renders nothing. */
  opened: boolean
  children: React.ReactNode
}) => (
  <div
    role="tabpanel"
    id={`panel-${id}`}
    aria-labelledby={`tab-${id}`}
    hidden={!active}
    className="pt-4"
  >
    {opened ? children : null}
  </div>
)
