import { cognitiveLevelNames } from './slo-labels'
import { cn } from '@/lib/utils'

/**
 * The thinking level a question tests: K, U or A.
 *
 * Shown on the question itself, not just on the syllabus map, so a student can
 * see at a glance whether they are being asked to recall something, explain it
 * or apply it — which is how the board decides what a question is worth.
 *
 * Green, and the same green everywhere, so it reads as information about the
 * question rather than as a warning or a score. It never carries a mark or a
 * right-or-wrong meaning, so it cannot be confused with the green used for a
 * correct answer: that one sits on the answer, this one on the question.
 */
export const CognitiveBadge = ({
  level,
  showName = false,
  className,
}: {
  level?: string | null
  /** Spell out "Knowledge" beside the letter, where there is room for it. */
  showName?: boolean
  className?: string
}) => {
  const code = (level ?? '').trim().toUpperCase()
  if (!(code in cognitiveLevelNames)) return null
  const name = cognitiveLevelNames[code as keyof typeof cognitiveLevelNames]
  return (
    <span
      title={`${name} question`}
      className={cn(
        'inline-flex items-center gap-1 rounded bg-emerald-500/15 px-1.5 py-0.5',
        'text-[10px] font-semibold text-emerald-700 dark:text-emerald-400',
        className,
      )}
    >
      {code}
      {showName && <span className="font-medium opacity-80">{name}</span>}
    </span>
  )
}
