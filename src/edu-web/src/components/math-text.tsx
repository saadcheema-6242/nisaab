import { memo } from 'react'
import { Streamdown } from 'streamdown'
import { normalizeMath } from '@/lib/math'
import { cn } from '@/lib/utils'

/** Short text with Markdown and formulas, e.g. a quiz option or flashcard side. */
export const MathText = memo(
  ({ children, className }: { children: string; className?: string }) => (
    <Streamdown
      className={cn(
        '[&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_p]:my-1',
        '[&_.katex-display]:my-2 [&_.katex-display]:overflow-x-auto',
        className,
      )}
      controls={false}
    >
      {normalizeMath(children)}
    </Streamdown>
  ),
)
