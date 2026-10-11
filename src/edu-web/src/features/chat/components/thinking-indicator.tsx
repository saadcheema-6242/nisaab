import { stageLabel } from '../chat-labels'
import type { ChatLang } from '../chat-labels'
import { ThinkingDots } from '@/components/ui/thinking-dots'
import { useSlowAfter } from '@/hooks/use-slow-after'

/**
 * Shown from the moment the student sends until the first word of the answer
 * appears: bouncing dots and a line saying what the tutor is actually doing.
 */
export const ThinkingIndicator = ({
  lang,
  label,
}: {
  lang: ChatLang
  /** What is happening now, e.g. "Checking the FBISE syllabus…" */
  label: string
}) => {
  const slow = useSlowAfter()

  return (
    <div className="space-y-1.5">
      <span className="inline-flex rounded-xl border bg-card px-3 py-2.5 text-muted-foreground">
        <ThinkingDots label={label} />
      </span>
      <p dir="auto" className="thinking-text text-sm text-muted-foreground">
        {label}
      </p>
      {slow && (
        <p dir="auto" className="text-xs text-muted-foreground/80">
          {stageLabel('slow', lang)}
        </p>
      )}
    </div>
  )
}
