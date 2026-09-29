import { ExportHeader, blocksToPdf, fileSlug, renderOffscreen } from './core'
import { MathText } from '@/components/math-text'

export async function exportNotePdf(title: string, content: string, subtitle?: string) {
  const { element, cleanup } = await renderOffscreen(
    <div style={{ padding: 8, fontSize: 14, lineHeight: 1.55 }}>
      <ExportHeader title={title} subtitle={subtitle} />
      <div data-note>
        <MathText className="[&_h1]:text-xl [&_h1]:font-bold [&_h2]:text-lg [&_h2]:font-semibold [&_h3]:font-semibold [&_li]:ml-5 [&_ol]:list-decimal [&_p]:my-2 [&_ul]:list-disc">
          {content}
        </MathText>
      </div>
    </div>,
  )
  try {
    // Every paragraph, heading, list or table is kept whole on a page
    const body = element.querySelector('[data-note] > *')
    Array.from(body?.children ?? []).forEach((child) => child.setAttribute('data-block', ''))
    await blocksToPdf(element, `${fileSlug(title)}.pdf`)
  } finally {
    cleanup()
  }
}
