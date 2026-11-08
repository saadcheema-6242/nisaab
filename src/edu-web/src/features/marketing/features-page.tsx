import { Link } from '@tanstack/react-router'
import { ArrowRightIcon } from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { Counter, Reveal, SectionHeading } from './bits'
import { MarketingLayout } from './marketing-layout'
import { PlayableQuestion } from './playable-question'
import { features, paperPattern, subjects, totalExamined } from './site-data'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const totalMarks = paperPattern.reduce((n, s) => n + s.marks, 0)

/** The 2026 paper, drawn to scale. Hovering a section opens it up. */
const PaperPattern = () => {
  const [active, setActive] = useState<string | null>(null)

  return (
    <div>
      <div className="flex h-16 w-full gap-1.5 overflow-hidden rounded-xl">
        {paperPattern.map((section, i) => (
          <motion.button
            key={section.section}
            type="button"
            onHoverStart={() => setActive(section.section)}
            onFocus={() => setActive(section.section)}
            onHoverEnd={() => setActive(null)}
            onBlur={() => setActive(null)}
            onClick={() =>
              setActive(active === section.section ? null : section.section)
            }
            className={cn(
              'relative flex items-center justify-center font-semibold transition-colors',
              i === 0 && 'bg-primary text-primary-foreground',
              i === 1 && 'bg-primary/70 text-primary-foreground',
              i === 2 && 'bg-primary/45 text-primary-foreground',
            )}
            style={{ flexGrow: section.marks }}
            animate={{
              opacity: active && active !== section.section ? 0.5 : 1,
            }}
          >
            {section.section}
          </motion.button>
        ))}
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        {paperPattern.map((section) => (
          <div
            key={section.section}
            className={cn(
              'rounded-xl border p-4 transition-colors',
              active === section.section && 'border-primary bg-primary/5',
            )}
          >
            <div className="flex items-baseline justify-between">
              <span className="font-semibold">Section {section.section}</span>
              <span className="text-primary font-mono text-sm">
                {section.marks} marks
              </span>
            </div>
            <div className="mt-1 text-sm font-medium">{section.title}</div>
            <div className="text-muted-foreground mt-0.5 text-sm">
              {section.detail}
            </div>
          </div>
        ))}
      </div>

      <p className="text-muted-foreground mt-5 text-sm">
        {totalMarks} marks in total, as FBISE sets the paper from 2026.
        Mathematics carries 100.
      </p>
    </div>
  )
}

export const FeaturesPage = () => (
  <MarketingLayout>
    <section className="mx-auto w-full max-w-6xl px-4 pt-20 pb-16 sm:px-6">
      <Reveal>
        <SectionHeading
          eyebrow="Features"
          title="Six things, all pointed at the same exam."
          blurb="NISAAB is built around the FBISE learning outcomes rather than around topics, so everything it gives you is something the paper can actually ask."
        />
      </Reveal>
    </section>

    <section className="border-y">
      <div className="mx-auto w-full max-w-6xl divide-y px-4 sm:px-6">
        {features.map((feature, i) => (
          <Reveal key={feature.slug}>
            <div className="grid gap-4 py-10 sm:grid-cols-[auto_1fr] sm:gap-10">
              <div className="text-primary/30 font-mono text-5xl font-bold tabular-nums">
                {String(i + 1).padStart(2, '0')}
              </div>
              <div className="max-w-2xl">
                <h3 className="text-xl font-semibold text-balance">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground mt-2 text-pretty">
                  {feature.blurb}
                </p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>

    <section className="mx-auto w-full max-w-6xl px-4 py-24 sm:px-6">
      <Reveal>
        <SectionHeading
          eyebrow="The 2026 pattern"
          title="Papers shaped like the real thing."
          blurb="Not a pile of questions — the actual structure, with the same weighting, the same question types and the same time limit."
        />
      </Reveal>
      <Reveal className="mt-12" delay={0.1}>
        <PaperPattern />
      </Reveal>
    </section>

    <section className="bg-muted/40 border-y">
      <div className="mx-auto w-full max-w-6xl px-4 py-24 sm:px-6">
        <Reveal>
          <SectionHeading
            eyebrow="Coverage"
            title="Every outcome, counted."
            blurb="FSc Part 1 is complete across all three groups. These are the outcomes in the database right now."
          />
        </Reveal>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {subjects.map((subject, i) => (
            <Reveal key={subject.code} delay={i * 0.06}>
              <div className="bg-card h-full rounded-2xl border p-5">
                <div className="flex items-center gap-2">
                  <span
                    className="size-2.5 rounded-full"
                    style={{ backgroundColor: subject.colour }}
                  />
                  <span className="text-sm font-semibold">{subject.name}</span>
                </div>
                <div className="mt-4 text-3xl font-bold tracking-tight">
                  <Counter to={subject.slos} />
                </div>
                <div className="text-muted-foreground text-sm">
                  learning outcomes
                </div>
                <div className="text-muted-foreground mt-2 text-xs">
                  {subject.examined} examinable
                </div>
              </div>
            </Reveal>
          ))}
        </div>
        <Reveal className="mt-8" delay={0.2}>
          <p className="text-muted-foreground text-sm">
            <span className="text-foreground font-semibold">
              {totalExamined}
            </span>{' '}
            of them carry marks in the exam. Those are the ones NISAAB drills
            hardest.
          </p>
        </Reveal>
      </div>
    </section>

    <section className="mx-auto w-full max-w-4xl px-4 py-24 sm:px-6">
      <Reveal>
        <SectionHeading
          className="mx-auto text-center"
          eyebrow="Try it"
          title="See how a question comes back."
        />
      </Reveal>
      <Reveal className="mt-10" delay={0.1}>
        <PlayableQuestion />
      </Reveal>
      <Reveal className="mt-10 text-center" delay={0.2}>
        <Button size="lg" asChild>
          <Link to="/sign-up">
            Start free <ArrowRightIcon className="size-4" />
          </Link>
        </Button>
      </Reveal>
    </section>
  </MarketingLayout>
)
