import { cognitiveLevelNames } from './slo-labels'
import { cn } from '@/lib/utils'

/**
 * The thinking level a question tests: K, U or A.
 *
 * Shown on the question itself, not just on the syllabus map, so a student can
 * see at a glance whether they are being asked to recall something, explain it
 * or apply it — which is how the board decides what a question is worth.
 */
export const CognitiveBadge = ({
  level,
  className,
}: {
  level?: string | null
  className?: string
}) => {
  const code = (level ?? '').trim().toUpperCase()
  if (!(code in cognitiveLevelNames)) return null
  const name = cognitiveLevelNames[code as keyof typeof cognitiveLevelNames]
  return (
    <span
      title={`${name} question`}
      className={cn(
        'bg-muted text-muted-foreground rounded px-1 text-[10px] font-semibold',
        className,
      )}
    >
      {code}
    </span>
  )
}
