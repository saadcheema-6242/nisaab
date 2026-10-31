import { cn } from '@/lib/utils'

/**
 * The NISAAB mark: the Urdu letter noon (ن), the first letter of نصاب.
 *
 * The geometry matches brand/nisaab-D-noon-tile-icon-light.svg, scaled from the
 * logo's 68-unit tile to a 24-unit box. Drawn in currentColor so it takes the
 * colour of whatever tile it is placed on.
 */
export const NisaabMark = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden
    className={cn('size-4', className)}
  >
    <path
      d="M5.65 8.47 Q5.65 16.94 12 16.94 Q18.35 16.94 18.35 8.47"
      stroke="currentColor"
      strokeWidth="2.47"
      strokeLinecap="round"
    />
    <circle cx="12" cy="5.65" r="1.59" fill="currentColor" />
  </svg>
)
