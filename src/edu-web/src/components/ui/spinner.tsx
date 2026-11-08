/**
 * The in-button spinner.
 *
 * A single ring with a gap, rotating. Deliberately plain: it appears
 * beside a verb like "Signing in", so the word carries the meaning and
 * the spinner only has to prove the page has not frozen.
 *
 * Drawn with a border rather than an SVG stroke so it inherits
 * currentColor and works on a filled button and an outline one without a
 * variant for each.
 *
 * Under prefers-reduced-motion the CSS animation stops, so this would be
 * a static broken ring - which is why the text beside it says what is
 * happening. The ring is hidden from assistive technology for the same
 * reason: the label is the announcement.
 */

import { cn } from '@/lib/utils'

export const Spinner = ({ className }: { className?: string }) => (
  <span
    aria-hidden
    className={cn(
      'inline-block size-4 shrink-0 animate-spin rounded-full',
      'border-2 border-current border-t-transparent opacity-80',
      'motion-reduce:animate-none',
      className,
    )}
  />
)
