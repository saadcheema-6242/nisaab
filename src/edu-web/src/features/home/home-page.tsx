import { Link, useNavigate, useSearch } from '@tanstack/react-router'
import { ArrowRightIcon } from 'lucide-react'
import { Suspense, useEffect } from 'react'
import { useAuth } from '@/hooks/use-auth'
import { Counter, Reveal, SectionHeading } from '@/features/marketing/bits'
import { Hero } from '@/features/marketing/hero'
import { MarketingLayout } from '@/features/marketing/marketing-layout'
import { PlayableQuestion } from '@/features/marketing/playable-question'
import { features, languages, stats } from '@/features/marketing/site-data'
import { Button } from '@/components/ui/button'

/**
 * Sends a signed-in student back to their dashboard.
 *
 * It lives in its own component behind its own Suspense boundary because
 * reading the auth atom suspends: done inline, the whole landing page would
 * sit on a "Loading..." fallback until Firebase answered, which on a slow
 * connection is the first thing a visitor would see.
 */
const AuthRedirect = () => {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const search = useSearch({ from: '/' })

  useEffect(() => {
    if (!isAuthenticated) return
    const redirectUrl = search?.redirect || sessionStorage.getItem('auth.redirect')
    if (redirectUrl) {
      sessionStorage.removeItem('auth.redirect')
      navigate({
        to: redirectUrl.startsWith('/dashboard')
          ? redirectUrl
          : `/dashboard${redirectUrl}`,
      })
    } else {
      navigate({ to: '/dashboard' })
    }
  }, [isAuthenticated, navigate, search?.redirect])

  return null
}

export const HomePage = () => {
  return (
    <MarketingLayout>
      <Suspense fallback={null}>
        <AuthRedirect />
      </Suspense>
      <Hero />

      {/* The numbers, which are the whole argument */}
      <section className="border-b">
        <div className="mx-auto grid w-full max-w-6xl grid-cols-2 gap-x-6 gap-y-10 px-4 py-16 sm:px-6 lg:grid-cols-4">
          {stats.map((stat, i) => (
            <Reveal key={stat.label} delay={i * 0.08}>
              <div className="text-primary text-4xl font-bold tracking-tight sm:text-5xl">
                <Counter to={stat.value} suffix={'suffix' in stat ? stat.suffix : ''} />
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
            eyebrow="What it does"
            title="Not a chatbot that happens to know physics."
            blurb="Everything is anchored to the learning outcome it belongs to, so the help you get is the help your paper will ask for."
          />
        </Reveal>

        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.slice(0, 6).map((feature, i) => (
            <Reveal key={feature.slug} delay={(i % 3) * 0.08}>
              <div className="bg-card hover:border-primary/40 h-full rounded-2xl border p-6 transition-colors">
                <h3 className="font-semibold text-balance">{feature.title}</h3>
                <p className="text-muted-foreground mt-2.5 text-sm text-pretty">
                  {feature.blurb}
                </p>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal className="mt-10" delay={0.1}>
          <Button variant="outline" asChild>
            <Link to="/features">
              See all of it <ArrowRightIcon className="size-4" />
            </Link>
          </Button>
        </Reveal>
      </section>

      {/* Let them actually use the thing before asking for a sign-up */}
      <section className="bg-muted/40 border-y">
        <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-24 sm:px-6 lg:grid-cols-2 lg:items-center">
          <Reveal>
            <SectionHeading
              eyebrow="Try it now"
              title="Have a go. No account needed."
              blurb="A real question in the FBISE style. Pick an answer and you get the reasoning back, the same way NISAAB explains it inside the app."
            />
          </Reveal>
          <Reveal delay={0.12}>
            <PlayableQuestion />
          </Reveal>
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 py-24 sm:px-6">
        <Reveal>
          <SectionHeading
            eyebrow="Three languages"
            title="Explained the way you think."
            blurb="Formulas and technical terms stay in English, exactly as your paper expects — only the explanation changes."
          />
        </Reveal>
        <div className="mt-12 grid gap-5 lg:grid-cols-3">
          {languages.map((language, i) => (
            <Reveal key={language.code} delay={i * 0.08}>
              <div className="bg-card h-full rounded-2xl border p-6">
                <div className="text-muted-foreground text-sm font-semibold">
                  {language.name}
                </div>
                <p
                  className="mt-3 text-lg text-pretty"
                  dir={language.code === 'ur' ? 'rtl' : 'ltr'}
                >
                  {language.sample}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="bg-primary text-primary-foreground">
        <div className="mx-auto w-full max-w-3xl px-4 py-24 text-center sm:px-6">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight text-balance sm:text-4xl">
              Start with the outcome you are weakest on.
            </h2>
            <p className="mt-4 text-lg text-pretty opacity-80">
              Pick your class and group, and the whole syllabus is waiting.
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
}
