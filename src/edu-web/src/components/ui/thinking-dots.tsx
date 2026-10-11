import { cn } from '@/lib/utils'

const DELAYS = ['0ms', '150ms', '300ms']

/**
 * Three bouncing dots, shown while the tutor is thinking or something is being
 * generated. Takes its colour from the text around it.
 */
export const ThinkingDots = ({
  className,
  label = 'Working',
}: {
  className?: string
  /** Read out by screen readers, which never see the animation */
  label?: string
}) => (
  <span
    className={cn('inline-flex items-center gap-1', className)}
    role="status"
    aria-label={label}
  >
    {DELAYS.map((delay) => (
      <span
        key={delay}
        aria-hidden
        className="thinking-dot size-1.5 rounded-full bg-current"
        style={{ animationDelay: delay }}
      />
    ))}
  </span>
)
