import { cn } from '@/lib/utils'

/**
 * The NISAAB mark: the Urdu letter noon (ن), the first letter of نصاب.
 * Drawn in currentColor so it sits on whatever background it is given.
 */
export const NisaabMark = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden
    className={cn('size-4', className)}
  >
    <path
      d="M6.84 7.2v6.5M17.16 7.2v6.5"
      stroke="currentColor"
      strokeWidth="2.04"
      strokeLinecap="round"
    />
    <path
      d="M6.84 13.7a5.16 5.16 0 0 0 10.32 0"
      stroke="currentColor"
      strokeWidth="2.04"
      strokeLinecap="round"
    />
    <circle cx="12" cy="5.04" r="1.2" fill="currentColor" />
  </svg>
)
