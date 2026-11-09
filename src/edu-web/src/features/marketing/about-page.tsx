import { Link } from '@tanstack/react-router'
import { ArrowRightIcon } from 'lucide-react'
import { Counter, Reveal, SectionHeading } from './bits'
import { MarketingLayout } from './marketing-layout'
import { college, stats, supervisor, team } from './site-data'
import { NisaabMark } from '@/components/nisaab-mark'
import { Button } from '@/components/ui/button'

const steps = [
  {
    title: 'The syllabus goes in first',
    body: 'The FBISE National Curriculum is loaded outcome by outcome — every SLO, its domain, and whether the board examines it. Nothing is generated until that map exists.',
  },
  {
    title: 'Every answer is tied to an outcome',
    body: 'When you ask a question, NISAAB finds the outcomes it touches and answers at the depth the board expects for those marks — not a general web answer.',
  },
  {
    title: 'Practice is aimed, not random',
    body: 'Questions are drawn against the outcomes you are weakest on, in the formats the paper uses: MCQs, short questions and extended response.',
  },
  {
    title: 'Marking closes the loop',
    body: 'Written answers come back marked against the outcome, so you can see which part of the answer earned the marks and which part lost them.',
  },
]

export const AboutPage = () => (
  <MarketingLayout>
    <section className="mx-auto w-full max-w-6xl px-4 pt-20 pb-16 sm:px-6">
      <Reveal>
        <SectionHeading
          eyebrow="About"
          title="Built by FSc students, for FSc students."
          blurb="NISAAB started from a problem we had ourselves: plenty of places to read about physics, almost nowhere to practise the exact outcomes FBISE puts on the paper."
        />
      </Reveal>
    </section>

    <section className="border-y">
      <div className="mx-auto grid w-full max-w-6xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2">
        <Reveal>
          <h2 className="text-2xl font-semibold text-balance">
            The gap we kept falling into
          </h2>
          <div className="text-muted-foreground mt-5 space-y-4 text-pretty">
            <p>
              An FSc student revises from a textbook written for the syllabus,
              then sits a paper written from the learning outcomes. Those are
              not the same document, and the distance between them is where
              marks go missing.
            </p>
            <p>
              Past papers help, but only after the fact. What was missing was
              something that knew the outcomes up front and could teach, test
              and mark against them — in the language the student actually
              thinks in.
            </p>
          </div>
        </Reveal>
        <Reveal delay={0.1}>
          <h2 className="text-2xl font-semibold text-balance">
            What we made instead
          </h2>
          <div className="text-muted-foreground mt-5 space-y-4 text-pretty">
            <p>
              NISAAB — <span dir="rtl">نصاب</span>, Urdu for syllabus — holds
              the whole FSc Part 1 curriculum for all three groups, outcome by
              outcome, and works only from it.
            </p>
            <p>
              It explains in English, Roman Urdu or Urdu while keeping formulas
              and technical terms in English, because that is how the paper has
              to be answered.
            </p>
          </div>
        </Reveal>
      </div>
    </section>

    <section className="mx-auto w-full max-w-6xl px-4 py-24 sm:px-6">
      <Reveal>
        <SectionHeading eyebrow="How it works" title="Four steps, in order." />
      </Reveal>
      <div className="mt-14 grid gap-6 sm:grid-cols-2">
        {steps.map((step, i) => (
          <Reveal key={step.title} delay={(i % 2) * 0.08}>
            <div className="bg-card h-full rounded-2xl border p-6">
              <div className="bg-primary/10 text-primary flex size-9 items-center justify-center rounded-lg font-mono text-sm font-bold">
                {i + 1}
              </div>
              <h3 className="mt-4 font-semibold text-balance">{step.title}</h3>
              <p className="text-muted-foreground mt-2 text-sm text-pretty">
                {step.body}
              </p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>

    <section className="bg-muted/40 border-y">
      <div className="mx-auto grid w-full max-w-6xl grid-cols-2 gap-x-6 gap-y-10 px-4 py-20 sm:px-6 lg:grid-cols-4">
        {stats.map((stat, i) => (
          <Reveal key={stat.label} delay={i * 0.08}>
            <div className="text-primary text-3xl font-bold tracking-tight sm:text-4xl">
              <Counter
                to={stat.value}
                suffix={'suffix' in stat ? stat.suffix : ''}
              />
            </div>
            <div className="mt-1.5 font-medium">{stat.label}</div>
            <div className="text-muted-foreground mt-0.5 text-sm text-pretty">
              {stat.detail}
            </div>
          </Reveal>
        ))}
      </div>
    </section>

    <section className="mx-auto w-full max-w-6xl px-4 py-24 sm:px-6">
      <Reveal>
        <SectionHeading
          eyebrow="The team"
          title="Three students and a supervisor."
          blurb={college}
        />
      </Reveal>
      <div className="mt-14 grid gap-6 sm:grid-cols-3">
        {team.map((person, i) => (
          <Reveal key={person.name} delay={i * 0.08}>
            <div className="bg-card h-full rounded-2xl border p-6">
              <span className="bg-primary text-primary-foreground flex size-10 items-center justify-center rounded-xl">
                <NisaabMark className="size-6" />
              </span>
              <div className="mt-4 font-semibold text-balance">
                {person.name}
              </div>
              <div className="text-muted-foreground mt-0.5 text-sm">
                {person.role}
              </div>
            </div>
          </Reveal>
        ))}
      </div>
      <Reveal className="mt-8" delay={0.2}>
        <p className="text-muted-foreground text-sm">
          Supervised by{' '}
          <span className="text-foreground font-medium">{supervisor}</span>.
        </p>
      </Reveal>
    </section>

    <section className="bg-primary text-primary-foreground">
      <div className="mx-auto w-full max-w-3xl px-4 py-24 text-center sm:px-6">
        <Reveal>
          <h2 className="text-3xl font-semibold text-balance sm:text-4xl">
            The syllabus is already in there.
          </h2>
          <p className="mt-4 text-lg opacity-80">
            Pick your class and group to begin.
          </p>
          <Button size="lg" variant="secondary" className="mt-8" asChild>
            <Link to="/sign-up">
              Start free <ArrowRightIcon className="size-4" />
            </Link>
          </Button>
        </Reveal>
      </div>
    </section>
  </MarketingLayout>
)
