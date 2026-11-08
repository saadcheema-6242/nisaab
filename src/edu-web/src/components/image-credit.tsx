/**
 * Who a diagram belongs to, shown underneath it.
 *
 * Diagrams come from openly licensed collections - Wikimedia Commons and the
 * like - which permit reuse on condition that the author, the licence and the
 * source are named wherever the picture appears. So this is not decoration
 * that can be dropped when space is tight: without it the picture may not be
 * used at all.
 *
 * A picture with no credit renders nothing, which is right for one the student
 * uploaded themselves.
 */
export type Credit = {
  author?: unknown
  licence?: unknown
  licence_url?: unknown
  source_url?: unknown
  source?: unknown
  title?: unknown
  line?: unknown
}

const text = (value: unknown) => (typeof value === 'string' ? value.trim() : '')

/** The one-line form, for a PDF or anywhere a link is no use. */
export const creditLine = (credit: unknown): string => {
  if (!credit || typeof credit !== 'object') return ''
  const c = credit as Credit
  const ready = text(c.line)
  if (ready) return ready
  const who = [text(c.title), text(c.author)].filter(Boolean).join(' - ')
  const licence = text(c.licence)
  const source = text(c.source)
  if (!who && !licence) return ''
  return `${who}${licence ? ` (${licence})` : ''}${source ? `, via ${source}` : ''}`
}

export const ImageCredit = ({
  credit,
  className = '',
}: {
  credit: unknown
  className?: string
}) => {
  if (!credit || typeof credit !== 'object') return null
  const c = credit as Credit
  const author = text(c.author)
  const title = text(c.title)
  const licence = text(c.licence)
  const licenceUrl = text(c.licence_url)
  const sourceUrl = text(c.source_url)
  const source = text(c.source)
  if (!author && !licence && !title) return null

  return (
    <div
      className={`text-muted-foreground text-[10px] leading-snug ${className}`}
    >
      {[title, author].filter(Boolean).join(' · ')}
      {licence && (
        <>
          {' · '}
          {licenceUrl ? (
            <a
              href={licenceUrl}
              target="_blank"
              rel="noopener noreferrer license"
              className="underline hover:text-foreground"
            >
              {licence}
            </a>
          ) : (
            licence
          )}
        </>
      )}
      {source && (
        <>
          {' · '}
          {sourceUrl ? (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-foreground"
            >
              {source}
            </a>
          ) : (
            source
          )}
        </>
      )}
    </div>
  )
}
