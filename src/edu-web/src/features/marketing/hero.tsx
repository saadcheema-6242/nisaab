import { Link } from '@tanstack/react-router'
import { ArrowRightIcon } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { Constellation } from './constellation'
import { subjects, totalSlos } from './site-data'
import { Button } from '@/components/ui/button'

/**
 * A chalk diagram draws itself, lifts off the board and leaves the syllabus
 * behind as a sky of learning outcomes. Skipped entirely for anyone who has
 * asked for reduced motion: they get the sky straight away.
 */
const ChalkIntro = () => {
  const chalk = '#E8EFE9'
  const stroke = {
    stroke: chalk,
    strokeWidth: 1.6,
    strokeLinecap: 'round' as const,
    fill: 'none',
    filter: 'url(#chalky)',
  }

  return (
    <motion.svg
      viewBox="0 0 300 200"
      aria-hidden
      className="pointer-events-none absolute top-1/2 left-1/2 w-[min(70vw,440px)] -translate-x-1/2 -translate-y-[62%]"
      initial={{ opacity: 1 }}
      animate={{ opacity: 0, y: -34, scale: 1.08 }}
      transition={{ delay: 2.1, duration: 1, ease: 'easeIn' }}
    >
      <defs>
        {/* roughens the edges so the strokes read as chalk, not vector */}
        <filter id="chalky">
          <feTurbulence
            baseFrequency="0.9"
            numOctaves="3"
            seed="7"
            result="noise"
          />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.2" />
        </filter>
      </defs>

      {[
        { d: 'M150 68 m-13 0 a13 13 0 1 0 26 0 a13 13 0 1 0 -26 0', delay: 0 },
        {
          d: 'M150 68 m-54 0 a54 22 0 1 0 108 0 a54 22 0 1 0 -108 0',
          delay: 0.3,
        },
        {
          d: 'M150 68 m-40 -36 a54 22 -58 1 0 80 72 a54 22 -58 1 0 -80 -72',
          delay: 0.55,
        },
        { d: 'M96 132 L204 132', delay: 0.95 },
        {
          d: 'M104 150 L128 150 M136 150 L150 150 M158 150 L196 150',
          delay: 1.15,
        },
      ].map((path) => (
        <motion.path
          key={path.d}
          d={path.d}
          {...stroke}
          initial={{ pathLength: 0, opacity: 0.9 }}
          animate={{ pathLength: 1 }}
          transition={{ delay: path.delay, duration: 0.8, ease: 'easeInOut' }}
        />
      ))}
    </motion.svg>
  )
}

export const Hero = () => {
  const still = useReducedMotion()
  const lead = still ? 0 : 2.4

  return (
    <section className="relative isolate flex min-h-[92vh] flex-col justify-center overflow-hidden bg-[#0E1512] text-white">
      <div className="absolute inset-0">
        <Constellation />
      </div>
      {/* keeps the text legible wherever the sky happens to be bright */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(14,21,18,0.82)_0%,rgba(14,21,18,0.35)_45%,rgba(14,21,18,0.9)_100%)]" />
      {!still && <ChalkIntro />}

      <motion.div
        className="relative z-10 mx-auto w-full max-w-4xl px-4 py-24 text-center sm:px-6"
        initial={still ? false : { opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: lead, duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-xs font-medium text-white/80 backdrop-blur-sm">
          <span className="relative flex size-1.5">
            <span className="bg-primary absolute inline-flex size-full animate-ping rounded-full opacity-75" />
            <span className="bg-primary relative inline-flex size-1.5 rounded-full" />
          </span>
          Aligned to the FBISE 2026 paper pattern
        </div>

        <h1 className="text-4xl font-semibold text-balance sm:text-6xl">
          The whole FBISE syllabus,
          <br className="hidden sm:block" /> one outcome at a time.
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-lg text-pretty text-white/70 sm:text-xl">
          Every star above is one of the{' '}
          <span className="font-semibold text-white">
            {totalSlos} learning outcomes
          </span>{' '}
          in FSc Part 1. NISAAB teaches, tests and marks you against each one —
          in English, Roman Urdu or اردو.
        </p>

        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button size="lg" asChild>
            <Link to="/sign-up">
              Start free <ArrowRightIcon className="size-4" />
            </Link>
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="border-white/20 bg-white/5 text-white hover:bg-white/10 hover:text-white"
            asChild
          >
            <Link to="/features">See what it does</Link>
          </Button>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
          {subjects.map((subject) => (
            <div
              key={subject.code}
              className="flex items-center gap-2 text-sm text-white/55"
            >
              <span
                className="size-2 rounded-full"
                style={{
                  backgroundColor: subject.colour,
                  boxShadow: `0 0 10px ${subject.colour}`,
                }}
              />
              {subject.name}
              <span className="font-mono text-xs text-white/35">
                {subject.slos}
              </span>
            </div>
          ))}
        </div>
      </motion.div>

      <div className="from-background pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t to-transparent" />
    </section>
  )
}
