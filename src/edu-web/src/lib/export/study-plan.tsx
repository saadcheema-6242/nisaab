import { BRAND, ExportHeader, blocksToPdf, fileSlug, renderOffscreen } from './core'
import { buildDocx, saveBlob, type DocBlock } from './docx'
import type { StudyPlanDto, StudyPlanItem } from '@/integrations/api/client'
import { brand } from '@/lib/brand'

const ACTION_LABELS: Record<string, string> = {
  read: 'Read',
  flashcards: 'Flashcards',
  quiz: 'Quiz',
  srq: 'Short question',
  paper: 'Paper',
}

const WHY: Record<string, string> = {
  struggling: 'Needs work',
  weak: 'Needs work',
  unknown: 'Not practised yet',
}

const spell = (minutes: number) => {
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `${hours} h ${rest} min` : `${hours} h`
}

const byDay = (items: ReadonlyArray<StudyPlanItem>) => {
  const days = [...new Set(items.map((item) => item.day))].sort((a, b) => a - b)
  return days.map((day) => ({
    day,
    steps: items.filter((item) => item.day === day),
  }))
}

/**
 * Where this plan lives in the app.
 *
 * The link carries the project, not the student: whoever opens it is
 * authenticated by their own session, so a shared copy opens the reader's own
 * account rather than the author's. Putting a user id in the URL would not
 * stop anyone - it would only leak the id, and invite a server that trusted
 * it to hand over someone else's plan.
 */
const planUrl = (projectId: string) =>
  `${window.location.origin}/dashboard/p/${projectId}/study-plan`

/** Who it was made for, said plainly rather than hidden in a link. */
const madeFor = (studentName?: string) => {
  const when = new Date().toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
  return studentName ? `Prepared for ${studentName} · ${when}` : `Prepared ${when}`
}

const Step = ({ item }: { item: StudyPlanItem }) => (
  <div
    data-block
    style={{
      border: '1px solid #e5e7eb',
      borderRadius: 8,
      padding: '8px 10px',
      marginBottom: 6,
    }}
  >
    <div style={{ fontSize: 10, color: '#6b7280', marginBottom: 2 }}>
      {[
        item.slo_code,
        ACTION_LABELS[item.action] ?? item.action,
        spell(item.minutes),
        WHY[item.standing ?? ''] ?? '',
        // A long plan comes back to the same outcome with harder work, so the
        // printed page has to say which pass a step is, or it reads as a
        // duplicate the student already did.
        item.pass_index > 0 ? 'Revision' : '',
      ]
        .filter(Boolean)
        .join(' · ')}
    </div>
    <div style={{ fontSize: 13, lineHeight: 1.5 }}>{item.title}</div>
    {item.tasks.length > 0 && (
      <ul style={{ margin: '3px 0 0', paddingLeft: 16 }}>
        {item.tasks.map((task, i) => (
          <li key={i} style={{ fontSize: 11, color: '#374151', lineHeight: 1.45 }}>
            {task}
          </li>
        ))}
      </ul>
    )}
    {item.target && (
      <div style={{ fontSize: 11, color: BRAND.green, fontWeight: 600, marginTop: 2 }}>
        {item.target}
      </div>
    )}
  </div>
)

/** The plan as a printable PDF, laid out day by day. */
export async function exportStudyPlanPdf(
  plan: StudyPlanDto,
  projectName?: string,
  studentName?: string,
) {
  const items = plan.content.items ?? []
  const total = items.reduce((sum, item) => sum + item.minutes, 0)
  const days = byDay(items)
  const themes = plan.content.day_themes ?? []

  const { element, cleanup } = await renderOffscreen(
    <div style={{ padding: 8, fontSize: 13, lineHeight: 1.5 }}>
      <ExportHeader
        title="Study plan"
        subtitle={[projectName, `${days.length} days · ${spell(total)} in total`]
          .filter(Boolean)
          .join(' · ')}
      />
      {plan.content.analysis && (
        <div data-block style={{ margin: '8px 0 12px', color: '#374151' }}>
          {plan.content.analysis}
        </div>
      )}
      {days.map(({ day, steps }) => (
        <div key={day}>
          <div
            data-block
            data-keep-with-next
            style={{
              fontSize: 13,
              fontWeight: 700,
              margin: '10px 0 4px',
              color: BRAND.green,
            }}
          >
            Day {day}
            {themes[day - 1] ? ` - ${themes[day - 1]}` : ''}
          </div>
          {steps.map((item, index) => (
            <Step key={`${day}-${index}`} item={item} />
          ))}
        </div>
      ))}
      {plan.content.encouragement && (
        <div data-block style={{ marginTop: 12, fontStyle: 'italic', color: '#374151' }}>
          {plan.content.encouragement}
        </div>
      )}
      <div data-block style={{ marginTop: 14, fontSize: 10, color: '#6b7280' }}>
        {madeFor(studentName)} · Open it in {brand.name}: {planUrl(plan.project_id)}
      </div>
    </div>,
  )
  try {
    await blocksToPdf(element, `${fileSlug('study plan')}.pdf`)
  } finally {
    cleanup()
  }
}

/** The plan as a Word document: real text, in a table, editable. */
export async function exportStudyPlanDocx(
  plan: StudyPlanDto,
  projectName?: string,
  studentName?: string,
) {
  const items = plan.content.items ?? []
  const total = items.reduce((sum, item) => sum + item.minutes, 0)
  const days = byDay(items)

  const blocks: DocBlock[] = [
    { kind: 'heading', text: 'Study plan', level: 1 },
    {
      kind: 'paragraph',
      text: [projectName, `${days.length} days`, `${spell(total)} in total`]
        .filter(Boolean)
        .join(' · '),
      muted: true,
    },
  ]

  if (plan.content.analysis) {
    blocks.push({ kind: 'paragraph', text: plan.content.analysis })
  }

  const themes = plan.content.day_themes ?? []
  for (const { day, steps } of days) {
    blocks.push({
      kind: 'heading',
      text: themes[day - 1] ? `Day ${day} - ${themes[day - 1]}` : `Day ${day}`,
      level: 2,
    })
    blocks.push({
      kind: 'table',
      head: ['Outcome', 'What', 'Time', 'To do'],
      rows: steps.map((item) => [
        item.slo_code,
        ACTION_LABELS[item.action] ?? item.action,
        spell(item.minutes),
        // One cell, several lines: the step, then the tasks, then the target.
        // The writer turns each newline into a real Word line break.
        [
          item.title,
          ...item.tasks.map((task) => `- ${task}`),
          item.target ? `Target: ${item.target}` : '',
        ]
          .filter(Boolean)
          .join('\n'),
      ]),
    })
  }

  if (plan.content.encouragement) {
    blocks.push({ kind: 'paragraph', text: plan.content.encouragement, italic: true })
  }

  blocks.push({ kind: 'paragraph', text: madeFor(studentName), muted: true })
  blocks.push({
    kind: 'link',
    text: `Open this plan in ${brand.name}`,
    url: planUrl(plan.project_id),
  })

  saveBlob(await buildDocx('Study plan', blocks), `${fileSlug('study plan')}.docx`)
}
