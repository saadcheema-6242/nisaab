import { ExportHeader, blocksToPdf, fileSlug, renderOffscreen } from './core'
import type { QuizQuestionDto } from '@/integrations/api/client'
import { MathText } from '@/components/math-text'
import { creditLine } from '@/components/image-credit'

const OPTIONS = ['a', 'b', 'c', 'd'] as const

/**
 * Fetch a diagram and turn it into a data URL.
 *
 * The printout is rasterised with a canvas, and a canvas that has drawn an
 * image from another origin is tainted and cannot be read back - which would
 * fail the whole export rather than lose one picture. Inlining the bytes
 * first avoids that. A picture that cannot be fetched is simply left out.
 */
const inlined = async (url: string): Promise<string | null> => {
  try {
    const response = await fetch(url)
    if (!response.ok) return null
    const blob = await response.blob()
    return await new Promise<string | null>((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = () => resolve(null)
      reader.readAsDataURL(blob)
    })
  } catch {
    return null
  }
}

/** Every question's diagram, by question id, ready to put in the page. */
export const inlineDiagrams = async (
  questions: ReadonlyArray<QuizQuestionDto>,
): Promise<Record<string, string>> => {
  const withImages = questions.filter((question) => question.image_url)
  const pairs = await Promise.all(
    withImages.map(async (question) => {
      const data = await inlined(question.image_url as string)
      return [question.id, data] as const
    }),
  )
  return Object.fromEntries(
    pairs.filter((pair): pair is readonly [string, string] => pair[1] !== null),
  )
}

/** A question's diagram with the attribution its licence requires. */
const Diagram = ({
  question,
  source,
}: {
  question: QuizQuestionDto
  source?: string
}) => {
  if (!source) return null
  const credit = creditLine(question.image_credit)
  return (
    <div style={{ paddingLeft: 20, marginTop: 6 }}>
      <img
        src={source}
        alt={question.image_alt ?? ''}
        style={{ maxWidth: 360, maxHeight: 260, border: '1px solid #e5e7eb', borderRadius: 6 }}
      />
      {/* Naming the author, licence and source is a condition of the licence
          the diagram was published under, and a printout is no exception. */}
      {credit && (
        <div style={{ fontSize: 9, color: '#6b7280', marginTop: 2, maxWidth: 360 }}>
          {credit}
        </div>
      )}
    </div>
  )
}

const QuizPrintout = ({
  title,
  subtitle,
  questions,
  withAnswers,
  diagrams,
}: {
  title: string
  subtitle?: string
  questions: ReadonlyArray<QuizQuestionDto>
  withAnswers: boolean
  diagrams: Record<string, string>
}) => (
  <div style={{ padding: 8, fontSize: 14 }}>
    <ExportHeader title={title} subtitle={subtitle} />
    <div data-block style={{ padding: '10px 0', fontSize: 13 }}>
      Name: ______________________ &nbsp;&nbsp; Class: __________ &nbsp;&nbsp; Score: ____ /{' '}
      {questions.length}
    </div>
    {questions.map((question, index) => (
      <div key={question.id} data-block style={{ padding: '8px 0' }}>
        <div style={{ display: 'flex', gap: 6, fontWeight: 600 }}>
          <span>{index + 1}.</span>
          <MathText>{question.question_text}</MathText>
        </div>
        <Diagram question={question} source={diagrams[question.id]} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', paddingLeft: 20, marginTop: 4 }}>
          {OPTIONS.map((option) => (
            <div key={option} style={{ display: 'flex', gap: 6 }}>
              <span>({option})</span>
              <MathText>{question[`option_${option}`]}</MathText>
            </div>
          ))}
        </div>
      </div>
    ))}
    {withAnswers && (
      <>
        <div data-block data-page-break style={{ padding: '4px 0 8px', borderBottom: '1px solid #9ca3af' }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>Answer key</div>
        </div>
        {questions.map((question, index) => (
          <div key={question.id} data-block style={{ padding: '6px 0', fontSize: 13 }}>
            <div style={{ fontWeight: 600 }}>
              {index + 1}. ({question.correct_option.toLowerCase()})
            </div>
            {question.explanation && (
              <MathText className="text-neutral-700">{question.explanation}</MathText>
            )}
          </div>
        ))}
      </>
    )}
  </div>
)

type QuizExport = {
  title: string
  subtitle?: string
  questions: ReadonlyArray<QuizQuestionDto>
  withAnswers?: boolean
}

/** Draws the printable quiz off-screen (call cleanup when done). */
export const renderQuizPrintout = async ({
  withAnswers = true,
  ...rest
}: QuizExport) =>
  renderOffscreen(
    <QuizPrintout
      {...rest}
      withAnswers={withAnswers}
      diagrams={await inlineDiagrams(rest.questions)}
    />,
  )

export async function exportQuizPdf({
  title,
  subtitle,
  questions,
  withAnswers = true,
}: {
  title: string
  subtitle?: string
  questions: ReadonlyArray<QuizQuestionDto>
  withAnswers?: boolean
}) {
  const { element, cleanup } = await renderQuizPrintout({
    title,
    subtitle,
    questions,
    withAnswers,
  })
  try {
    await blocksToPdf(element, `${fileSlug(title)}${withAnswers ? '' : '-questions'}.pdf`)
  } finally {
    cleanup()
  }
}
