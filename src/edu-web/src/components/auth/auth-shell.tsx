/**
 * The frame around signing in, signing up and confirming an email.
 *
 * These three pages were a heading and a stack of fields on a flat
 * background: the only screens in the product with no identity on them at
 * all, and the first screen anyone who is handed the laptop will see.
 *
 * What it adds:
 *
 *   The mark, drawn rather than placed. The noon's bowl is a smile, so it
 *   is animated as one - the stroke draws itself left to right and the dot
 *   drops in after. It runs once, in under a second, and it is the only
 *   motion on the page.
 *
 *   A card, so the form is an object on a surface instead of text floating
 *   in the middle of the viewport.
 *
 *   A background wash of two very faint brand-coloured pools. Enough that
 *   the page is not white; not enough to notice unless looked for.
 *
 * Every animation is skipped under prefers-reduced-motion, which on this
 * project is not hypothetical - the machine the app is demonstrated from
 * has it switched on, so the still path is the one most likely to be seen.
 */

import { motion, useReducedMotion } from 'motion/react'
import { cn } from '@/lib/utils'

/** The mark, drawing itself: the smile, then the dot. */
const DrawnMark = ({ className }: { className?: string }) => {
  const still = useReducedMotion()

  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className={cn('size-7', className)}
    >
      <motion.path
        d="M5.65 8.47 Q5.65 16.94 12 16.94 Q18.35 16.94 18.35 8.47"
        stroke="currentColor"
        strokeWidth="2.47"
        strokeLinecap="round"
        initial={still ? false : { pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{
          pathLength: { duration: 0.65, ease: [0.22, 1, 0.36, 1] },
          opacity: { duration: 0.15 },
        }}
      />
      <motion.circle
        cx="12"
        cy="5.65"
        r="1.59"
        fill="currentColor"
        initial={still ? false : { scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        // Lands as the smile finishes, so it reads as one gesture.
        transition={{
          delay: still ? 0 : 0.55,
          type: 'spring',
          stiffness: 520,
          damping: 24,
        }}
        style={{ originX: '12px', originY: '5.65px' }}
      />
    </svg>
  )
}

export const AuthShell = ({
  title,
  blurb,
  children,
  footer,
}: {
  title: string
  blurb?: string
  children: React.ReactNode
  /** Sign-up link, privacy line - anything below the card. */
  footer?: React.ReactNode
}) => {
  const still = useReducedMotion()

  return (
    <div className="bg-background relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      {/* The wash. Behind everything, ignores the pointer, hidden from
          assistive technology: it carries no information. */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="bg-primary/[0.07] absolute -top-32 -left-24 size-[28rem] rounded-full blur-3xl" />
        <div className="bg-chart-2/[0.06] absolute -right-24 -bottom-32 size-[26rem] rounded-full blur-3xl" />
      </div>

      <motion.div
        className="relative w-full max-w-md"
        initial={still ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="mb-7 flex flex-col items-center text-center">
          <div className="bg-primary text-primary-foreground shadow-md mb-4 grid size-12 place-items-center rounded-2xl">
            <DrawnMark />
          </div>
          {/* h1, so it takes the serif from the global sheet. */}
          <h1 className="text-foreground text-3xl font-semibold">{title}</h1>
          {blurb && (
            <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
              {blurb}
            </p>
          )}
        </div>

        <div className="bg-card border-border/70 rounded-2xl border p-6 shadow-lg sm:p-7">
          {children}
        </div>

        {footer && <div className="mt-6 space-y-3 text-center">{footer}</div>}
      </motion.div>
    </div>
  )
}

/**
 * A labelled rule, for "or" between the password form and Google.
 *
 * Its own component because all three auth pages want it and it is fiddly
 * enough that a second copy would end up a pixel different.
 */
export const OrRule = ({ children = 'or' }: { children?: React.ReactNode }) => (
  <div className="relative py-1">
    <div className="absolute inset-0 flex items-center" aria-hidden>
      <span className="border-border/70 w-full border-t" />
    </div>
    <div className="relative flex justify-center">
      <span className="bg-card text-muted-foreground px-3 text-xs tracking-[0.08em] uppercase">
        {children}
      </span>
    </div>
  </div>
)

/** The sign-in / sign-up failure box, identical on every auth page. */
export const AuthError = ({ children }: { children: React.ReactNode }) => (
  <div
    role="alert"
    className="border-destructive/25 bg-destructive/10 rounded-lg border p-3"
  >
    <p className="text-destructive text-sm">{children}</p>
  </div>
)

/** The Google G, in its own colours, which is what Google's terms require. */
export const GoogleMark = () => (
  <svg viewBox="0 0 18 18" aria-hidden className="size-4">
    <path
      fill="#4285F4"
      d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.91c1.7-1.57 2.69-3.88 2.69-6.62Z"
    />
    <path
      fill="#34A853"
      d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.91-2.26c-.81.54-1.84.86-3.05.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.34A9 9 0 0 0 9 18Z"
    />
    <path
      fill="#FBBC05"
      d="M3.97 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.94H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.06l3.01-2.34Z"
    />
    <path
      fill="#EA4335"
      d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.94l3.01 2.34C4.68 5.16 6.66 3.58 9 3.58Z"
    />
  </svg>
)
