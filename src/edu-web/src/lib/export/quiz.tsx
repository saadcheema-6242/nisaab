import { ExportHeader, blocksToPdf, fileSlug, renderOffscreen } from './core'
import type { QuizQuestionDto } from '@/integrations/api/client'
import { MathText } from '@/components/math-text'

const OPTIONS = ['a', 'b', 'c', 'd'] as const

const QuizPrintout = ({
  title,
  subtitle,
  questions,
  withAnswers,
}: {
  title: string
  subtitle?: string
  questions: ReadonlyArray<QuizQuestionDto>
  withAnswers: boolean
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
export const renderQuizPrintout = ({ withAnswers = true, ...rest }: QuizExport) =>
  renderOffscreen(<QuizPrintout {...rest} withAnswers={withAnswers} />)

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
