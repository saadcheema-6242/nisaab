/**
 * What a shared link opens: a quiz or a paper, as a document.
 *
 * This is the only page in NISAAB a person can reach without an account,
 * and it is deliberately not an app screen. No sidebar, no theme, no
 * navigation, nothing interactive except the two buttons at the top.
 * Somebody opened a link a friend sent them; they are reading, not
 * using a product.
 *
 * It is built to print. Pressing Ctrl+P should produce something that
 * looks like a real paper rather than a screenshot of a web page, so:
 *
 *   the page is always light, whatever theme the reader's device
 *   prefers, because that is what comes out of a printer;
 *
 *   it is set in the serif at a readable size with a measured column
 *   width, rather than stretched across a wide screen;
 *
 *   `print:` rules drop the buttons, open every explanation, remove
 *   shadows and tints that waste ink, and keep a question from being
 *   split across two pages;
 *
 *   @page gives it real margins, and a footer line carries the source,
 *   so a printed copy says where it came from.
 *
 * The answers are shown. The reader cannot attempt this, so a quiz with
 * its answers hidden is a list of questions they can do nothing with.
 */

import { useEffect, useState } from 'react'
import { CheckIcon, PrinterIcon } from 'lucide-react'
import type { SharedQuestion, SharedView } from '@/data-acess/shares'
import { NisaabMark } from '@/components/nisaab-mark'
import { MathText } from '@/components/math-text'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { readShare } from '@/data-acess/shares'
import { brand } from '@/lib/brand'
import { cn } from '@/lib/utils'

const LETTERS = ['a', 'b', 'c', 'd'] as const

const optionText = (q: SharedQuestion, letter: (typeof LETTERS)[number]) =>
  ({ a: q.option_a, b: q.option_b, c: q.option_c, d: q.option_d })[letter]

const QuestionBlock = ({ q, n }: { q: SharedQuestion; n: number }) => (
  // break-inside-avoid is the whole reason this is a <section>: without
  // it a question's stem prints on one page and its options on the next.
  <section className="break-inside-avoid border-b border-neutral-200 py-5 last:border-b-0">
    <div className="flex gap-3">
      <span className="w-6 shrink-0 text-right text-sm font-semibold text-neutral-500 tabular-nums">
        {n}.
      </span>
      <div className="min-w-0 flex-1">
        <MathText className="font-medium leading-relaxed text-neutral-900">
          {q.question_text}
        </MathText>

        {q.image_path && (
          <img
            src={q.image_path}
            alt={q.image_alt ?? ''}
            className="my-3 max-h-64 rounded border border-neutral-200"
          />
        )}

        <ol className="mt-3 space-y-1.5">
          {LETTERS.map((letter) => {
            const right = q.correct_option.toLowerCase() === letter
            return (
              <li
                key={letter}
                className={cn(
                  'flex gap-2 rounded px-2 py-1 text-[0.95rem] leading-relaxed',
                  // The correct option is marked with a tick and a word,
                  // not with colour alone: colour does not survive a
                  // black-and-white printer, and does not reach a reader
                  // who cannot distinguish it.
                  right && 'bg-emerald-50 print:bg-transparent',
                )}
              >
                <span
                  className={cn(
                    'w-5 shrink-0 font-semibold text-neutral-500',
                    right && 'text-emerald-700',
                  )}
                >
                  {letter.toUpperCase()}.
                </span>
                <MathText className="min-w-0 flex-1 text-neutral-800">
                  {optionText(q, letter)}
                </MathText>
                {right && (
                  <span className="shrink-0 text-xs font-semibold text-emerald-700">
                    <CheckIcon className="mr-0.5 inline size-3" />
                    correct
                  </span>
                )}
              </li>
            )
          })}
        </ol>

        {q.explanation && (
          <div className="mt-3 border-l-2 border-emerald-600 bg-neutral-50 px-3 py-2 print:bg-transparent">
            <p className="mb-0.5 text-[0.7rem] font-semibold tracking-wide text-emerald-800 uppercase">
              Why
            </p>
            <MathText className="text-sm leading-relaxed text-neutral-700">
              {q.explanation}
            </MathText>
          </div>
        )}

        {(q.slo_code || q.cognitive_level) && (
          <p className="mt-2 text-xs text-neutral-400">
            {q.slo_code}
            {q.slo_code && q.cognitive_level ? ' · ' : ''}
            {q.cognitive_level}
          </p>
        )}
      </div>
    </div>
  </section>
)

/** A paper's sections, rendered as a document rather than an exam to sit. */
const PaperBody = ({ view }: { view: SharedView }) => (
  <>
    {(view.sections ?? []).map((section) => (
      <section key={section.id} className="mb-6">
        <h2 className="mb-3 border-b border-neutral-300 pb-1 font-serif text-lg font-semibold text-neutral-900">
          {section.title}
        </h2>
        <ol className="space-y-4">
          {section.items.map((raw, i) => {
            const item = raw as {
              id?: string
              question_text?: string
              question?: string
              marks?: number
              type?: string
            }
            return (
              <li
                key={item.id ?? i}
                className="break-inside-avoid flex gap-3 text-[0.95rem]"
              >
                <span className="w-6 shrink-0 text-right font-semibold text-neutral-500 tabular-nums">
                  {i + 1}.
                </span>
                <div className="min-w-0 flex-1">
                  <MathText className="leading-relaxed text-neutral-900">
                    {item.question_text ?? item.question ?? ''}
                  </MathText>
                </div>
                {item.marks !== undefined && (
                  <span className="shrink-0 text-sm text-neutral-500">
                    [{item.marks}]
                  </span>
                )}
              </li>
            )
          })}
        </ol>
      </section>
    ))}
  </>
)

export const SharedPage = ({ token }: { token: string }) => {
  const [view, setView] = useState<SharedView | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    readShare(token)
      .then((v) => alive && setView(v))
      .catch(
        (e: unknown) =>
          alive &&
          setError(
            e instanceof Error ? e.message : 'That link could not be opened.',
          ),
      )
    return () => {
      alive = false
    }
  }, [token])

  if (error) {
    return (
      <div className="grid min-h-screen place-items-center bg-neutral-50 px-4">
        <div className="max-w-sm text-center">
          <div className="mx-auto mb-4 grid size-12 place-items-center rounded-2xl bg-[#1F6B4A] text-white">
            <NisaabMark className="size-6" />
          </div>
          <h1 className="font-serif text-2xl font-semibold text-neutral-900">
            Link not available
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-neutral-600">
            {error}
          </p>
          <a
            href="/"
            className="mt-5 inline-block text-sm font-medium text-[#1F6B4A] underline-offset-4 hover:underline"
          >
            See what {brand.name} is
          </a>
        </div>
      </div>
    )
  }

  if (!view) {
    return (
      <div className="grid min-h-screen place-items-center bg-neutral-50">
        <p className="flex items-center gap-2 text-sm text-neutral-500">
          <Spinner className="size-4" /> Opening…
        </p>
      </div>
    )
  }

  const when = new Date(view.shared_at).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  return (
    // Fixed light colours rather than theme tokens: this is a document,
    // and a document is the colour of paper.
    <div className="min-h-screen bg-neutral-100 py-8 print:bg-white print:py-0">
      <article className="mx-auto max-w-[46rem] bg-white px-8 py-10 shadow-sm print:max-w-none print:px-0 print:py-0 print:shadow-none">
        <header className="mb-8 border-b-2 border-[#1F6B4A] pb-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="grid size-9 place-items-center rounded-lg bg-[#1F6B4A] text-white">
                <NisaabMark className="size-5" />
              </div>
              <div>
                <p className="font-serif text-lg leading-none font-bold text-[#1F6B4A]">
                  {brand.name}
                </p>
                <p className="text-xs text-neutral-500">
                  {view.kind === 'quiz' ? 'Shared quiz' : 'Shared paper'}
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="print:hidden"
              onClick={() => window.print()}
            >
              <PrinterIcon /> Print or save as PDF
            </Button>
          </div>

          <h1 className="mt-5 font-serif text-3xl leading-tight font-semibold text-neutral-900">
            {view.title ?? 'Untitled'}
          </h1>
          <p className="mt-2 text-sm text-neutral-500">
            Shared by {view.shared_by} · {when}
            {view.questions ? ` · ${view.questions.length} questions` : ''}
            {view.total_marks ? ` · ${view.total_marks} marks` : ''}
            {view.time_limit_minutes
              ? ` · ${view.time_limit_minutes} minutes`
              : ''}
          </p>
          {view.description && (
            <p className="mt-2 text-sm leading-relaxed text-neutral-600">
              {view.description}
            </p>
          )}
          {/* Said plainly, so nobody waits for a Start button. */}
          <p className="mt-4 border-l-2 border-neutral-300 bg-neutral-50 px-3 py-2 text-xs text-neutral-600 print:bg-transparent">
            This is a read-only copy with the answers shown. It cannot be
            attempted here.
          </p>
        </header>

        {view.kind === 'quiz' ? (
          <div>
            {(view.questions ?? []).map((q, i) => (
              <QuestionBlock key={q.id} q={q} n={i + 1} />
            ))}
          </div>
        ) : (
          <PaperBody view={view} />
        )}

        <footer className="mt-10 border-t border-neutral-200 pt-4 text-center">
          <p className="text-xs text-neutral-400">{brand.notice}</p>
          <p className="mt-1 text-xs text-neutral-400">
            Made with {brand.name} · nisaab.muhammadsaadcheema.com
          </p>
        </footer>
      </article>
    </div>
  )
}

export default SharedPage
