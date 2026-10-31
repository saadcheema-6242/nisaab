import { motion, useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/** Fades a block up as it comes into view, once. */
export const Reveal = ({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode
  delay?: number
  className?: string
}) => {
  const still = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={still ? false : { opacity: 0, y: 22 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.55, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}

/**
 * Counts up to a number when it scrolls into view.
 *
 * The count is decoration; the number is the point. So this leans on a plain
 * scroll check rather than an IntersectionObserver, and a timer guarantees the
 * real figure appears even if the frame loop never runs — a visitor left
 * staring at "0 learning outcomes" would be worse than no animation at all.
 */
export const Counter = ({
  to,
  suffix = '',
  className,
}: {
  to: number
  suffix?: string
  className?: string
}) => {
  const ref = useRef<HTMLSpanElement>(null)
  const [shown, setShown] = useState(0)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    // Asked directly rather than through useReducedMotion, which reports null
    // until it resolves; a counter reading that null would start a frame loop
    // for someone who asked for no motion.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setShown(to)
      return
    }

    let frame = 0
    let safety = 0
    let started = false

    const count = () => {
      if (started) return
      const box = element.getBoundingClientRect()
      if (box.top > window.innerHeight - 40 || box.bottom < 0) return
      started = true
      window.removeEventListener('scroll', count)
      window.removeEventListener('resize', count)

      const begin = performance.now()
      const step = (now: number) => {
        const t = Math.min(1, (now - begin) / 1400)
        setShown(Math.round(to * (1 - (1 - t) ** 3)))
        if (t < 1) frame = requestAnimationFrame(step)
      }
      frame = requestAnimationFrame(step)
      // Frames are paused in a background tab; timers are not.
      safety = window.setTimeout(() => setShown(to), 2200)
    }

    window.addEventListener('scroll', count, { passive: true })
    window.addEventListener('resize', count)
    count()

    return () => {
      window.removeEventListener('scroll', count)
      window.removeEventListener('resize', count)
      cancelAnimationFrame(frame)
      clearTimeout(safety)
    }
  }, [to])

  return (
    <span ref={ref} className={className}>
      {shown.toLocaleString()}
      {suffix}
    </span>
  )
}

export const SectionHeading = ({
  eyebrow,
  title,
  blurb,
  className,
}: {
  eyebrow?: string
  title: ReactNode
  blurb?: ReactNode
  className?: string
}) => (
  <div className={cn('max-w-2xl', className)}>
    {eyebrow && (
      <div className="text-primary text-sm font-semibold tracking-wide uppercase">
        {eyebrow}
      </div>
    )}
    <h2 className="mt-2 text-3xl font-bold tracking-tight text-balance sm:text-4xl">
      {title}
    </h2>
    {blurb && (
      <p className="text-muted-foreground mt-4 text-lg text-pretty">{blurb}</p>
    )}
  </div>
)
