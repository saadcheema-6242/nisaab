import { BRAND, ExportHeader, blocksToPdf, fileSlug, renderOffscreen } from './core'
import type {
  PaperDto,
  PaperItemDto,
  PaperItemResultDto,
} from '@/integrations/api/client'
import { MathText } from '@/components/math-text'

/**
 * A printable FBISE paper.
 *
 * Three modes, because a paper is used three different ways: sat on paper,
 * reviewed with your own answers beside it, or studied from with the full
 * solutions.
 */
export type PaperMode = 'blank' | 'answers' | 'solutions'

const OPTIONS = ['a', 'b', 'c', 'd'] as const

const optionText = (item: PaperItemDto, key: string) => {
  const value = (item.options as Record<string, unknown> | null)?.[key]
  return typeof value === 'string' ? value : ''
}

const marksLabel = (marks: number) =>
  `${Number.isInteger(marks) ? marks : marks.toFixed(2).replace(/0$/, '')} ${marks === 1 ? 'mark' : 'marks'}`

const Meta = ({ item }: { item: PaperItemDto }) => (
  <span style={{ fontSize: 10, color: '#6b7280', whiteSpace: 'nowrap' }}>
    {[item.cognitive_level, item.slo_code, marksLabel(item.marks)]
      .filter(Boolean)
      .join(' · ')}
  </span>
)

/** Ruled space to write a written answer in, sized by what the marks expect. */
const WritingSpace = ({ marks }: { marks: number }) => (
  <div style={{ paddingTop: 6 }}>
    {Array.from({ length: Math.max(3, Math.round(marks * 1.5)) }).map((_, i) => (
      <div key={i} style={{ borderBottom: '1px solid #d1d5db', height: 22 }} />
    ))}
  </div>
)

const Question = ({
  item,
  number,
  mode,
  given,
  result,
}: {
  item: PaperItemDto
  number: number
  mode: PaperMode
  given?: string
  result?: PaperItemResultDto
}) => {
  const correct = (result?.correct_option ?? '').toLowerCase()
  const chosen = (result?.chosen ?? given ?? '').toLowerCase()

  return (
    <div data-block style={{ padding: '8px 0' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
        <span style={{ fontWeight: 700 }}>{number}.</span>
        <div style={{ flex: 1 }}>
          <MathText>{item.question}</MathText>
        </div>
        <Meta item={item} />
      </div>

      {item.type === 'mcq' ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '4px 16px',
            paddingLeft: 22,
            marginTop: 4,
          }}
        >
          {OPTIONS.map((option) => {
            const isCorrect = mode === 'solutions' && correct === option
            const isChosen = mode !== 'blank' && chosen === option
            return (
              <div
                key={option}
                style={{
                  display: 'flex',
                  gap: 6,
                  fontWeight: isCorrect ? 700 : 400,
                  color: isCorrect ? BRAND.green : undefined,
                }}
              >
                <span>
                  ({option}){isChosen ? ' ←' : ''}
                </span>
                <MathText>{optionText(item, option)}</MathText>
              </div>
            )
          })}
        </div>
      ) : mode === 'blank' ? (
        <div style={{ paddingLeft: 22 }}>
          <WritingSpace marks={item.marks} />
        </div>
      ) : null}

      {mode !== 'blank' && item.type !== 'mcq' && (
        <div style={{ paddingLeft: 22, marginTop: 4, fontSize: 13 }}>
          <div style={{ color: '#6b7280' }}>Your answer</div>
          <MathText>{result?.answer || given || '—'}</MathText>
        </div>
      )}

      {mode === 'solutions' && (
        <div
          style={{
            paddingLeft: 22,
            marginTop: 6,
            borderLeft: `2px solid ${BRAND.tint}`,
            fontSize: 13,
          }}
        >
          {item.type === 'mcq' ? (
            <>
              <div style={{ fontWeight: 700, color: BRAND.green }}>
                Answer: ({correct || '—'})
              </div>
              {result?.explanation && <MathText>{result.explanation}</MathText>}
            </>
          ) : (
            <>
              <div style={{ fontWeight: 700, color: BRAND.green }}>Model answer</div>
              <MathText>{result?.model_answer || '—'}</MathText>
              {result?.marking?.feedback && (
                <>
                  <div style={{ fontWeight: 700, marginTop: 4 }}>
                    Examiner&rsquo;s note ({result.marking.awarded_marks} /{' '}
                    {result.marking.max_marks})
                  </div>
                  <MathText>{result.marking.feedback}</MathText>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

const PaperPrintout = ({
  paper,
  subtitle,
  mode,
}: {
  paper: PaperDto
  subtitle?: string
  mode: PaperMode
}) => {
  const results = new Map<string, PaperItemResultDto>(
    (paper.result?.items ?? []).map((item) => [item.id, item]),
  )
  const answers = (paper.answers ?? {}) as Record<string, string>
  let number = 0

  return (
    <div style={{ padding: 8, fontSize: 14 }}>
      <ExportHeader title={paper.title} subtitle={subtitle} />
      <div
        data-block
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          padding: '8px 0',
          fontSize: 13,
          borderBottom: '1px solid #e5e7eb',
        }}
      >
        <span>
          Total marks: <strong>{paper.total_marks}</strong>
        </span>
        <span>Time: {paper.time_limit_minutes} minutes</span>
        {mode === 'solutions' && paper.result ? (
          <span>
            Score: <strong>{paper.result.score}</strong> / {paper.result.max_score} (
            {paper.result.percent}%)
          </span>
        ) : (
          <span>Name: ____________________</span>
        )}
      </div>

      {paper.sections.map((section) => (
        <div key={section.id}>
          <div
            data-block
            style={{
              padding: '12px 0 6px',
              fontWeight: 700,
              fontSize: 15,
              color: BRAND.green,
            }}
          >
            {section.title}
          </div>
          {section.items.map((item) => {
            number += 1
            return (
              <div key={item.id}>
                {item.stimulus && (
                  <div
                    data-block
                    style={{
                      background: BRAND.tint,
                      padding: 8,
                      borderRadius: 6,
                      margin: '6px 0',
                      fontSize: 13,
                    }}
                  >
                    <MathText>{item.stimulus}</MathText>
                  </div>
                )}
                <Question
                  item={item}
                  number={number}
                  mode={mode}
                  given={answers[item.id]}
                  result={results.get(item.id)}
                />
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}

const SUFFIX: Record<PaperMode, string> = {
  blank: '-to-attempt',
  answers: '-my-answers',
  solutions: '-solutions',
}

export async function exportPaperPdf({
  paper,
  subtitle,
  mode,
}: {
  paper: PaperDto
  subtitle?: string
  mode: PaperMode
}) {
  const { element, cleanup } = await renderOffscreen(
    <PaperPrintout paper={paper} subtitle={subtitle} mode={mode} />,
  )
  try {
    await blocksToPdf(element, `${fileSlug(paper.title)}${SUFFIX[mode]}.pdf`)
  } finally {
    cleanup()
  }
}
