import { createRoot } from 'react-dom/client'
import type { ReactNode } from 'react'
import { brand } from '@/lib/brand'

/**
 * Exports are drawn in the browser from the same components as the screen (so
 * formulas and Urdu look identical), captured as images, and placed on PDF pages.
 * The heavy libraries are loaded only when someone downloads something.
 */

// Light colours regardless of the app theme, since exports are printed or shared
export const PAGE_STYLE: React.CSSProperties = {
  background: '#ffffff',
  color: '#111827',
  colorScheme: 'light',
  fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif',
}

/** Mounts a layout off-screen, waits until it has painted, and returns its root element. */
export async function renderOffscreen(node: ReactNode, width: number | 'auto' = 794) {
  const container = document.createElement('div')
  Object.assign(container.style, {
    position: 'fixed',
    left: '-100000px',
    top: '0',
    width: width === 'auto' ? 'max-content' : `${width}px`,
    zIndex: '-1',
  })
  document.body.appendChild(container)
  const root = createRoot(container)
  root.render(<div style={PAGE_STYLE}>{node}</div>)
  // Let React commit, then wait for fonts and two frames so everything has painted
  await new Promise((resolve) => setTimeout(resolve, 50))
  await document.fonts.ready
  // Two frames, or a short timeout when the tab is in the background (frames pause there)
  await Promise.race([
    new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
    new Promise((resolve) => setTimeout(resolve, 300)),
  ])
  return {
    element: container.firstElementChild as HTMLElement,
    cleanup: () => {
      root.unmount()
      container.remove()
    },
  }
}

/**
 * The fonts (incl. KaTeX's math fonts) used anywhere in an export's layout, embedded as
 * CSS. Collecting them is slow, so it is done once per export from the whole layout
 * (woff2 only) and passed to every capture of its parts.
 */
export async function fontsFor(root: HTMLElement) {
  const { getFontEmbedCSS } = await import('html-to-image')
  return getFontEmbedCSS(root, { preferredFontFormat: 'woff2' })
}

export async function toCanvas(element: HTMLElement, pixelRatio = 2, fontCss?: string) {
  const { toCanvas: capture } = await import('html-to-image')
  return capture(element, {
    pixelRatio,
    backgroundColor: '#ffffff',
    preferredFontFormat: 'woff2',
    fontEmbedCSS: fontCss ?? (await fontsFor(element)),
  })
}

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}

export const fileSlug = (text: string) =>
  text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60) || 'download'

/**
 * Places each block (an element marked data-block) on A4 pages without splitting it;
 * a block marked data-page-break starts a new page. Adds page numbers and the app name.
 */
export async function blocksToPdf(
  root: HTMLElement,
  filename: string,
  { orientation = 'portrait' as 'portrait' | 'landscape', margin = 12, gap = 3 } = {},
) {
  const { jsPDF } = await import('jspdf')
  const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation })
  const pageWidth = pdf.internal.pageSize.getWidth()
  const pageHeight = pdf.internal.pageSize.getHeight()
  const contentWidth = pageWidth - margin * 2
  const bottom = pageHeight - margin - 6 // room for the footer
  let y = margin

  const blocks = Array.from(root.querySelectorAll<HTMLElement>('[data-block]'))
  const fontCss = await fontsFor(root)
  for (const block of blocks) {
    if (block.dataset.pageBreak !== undefined && y > margin) {
      pdf.addPage()
      y = margin
    }
    const canvas = await toCanvas(block, 2, fontCss)
    let height = (canvas.height * contentWidth) / canvas.width
    let width = contentWidth
    if (height > bottom - margin) {
      // Taller than a page: shrink to fit
      width = (contentWidth * (bottom - margin)) / height
      height = bottom - margin
    }
    if (y + height > bottom && y > margin) {
      pdf.addPage()
      y = margin
    }
    pdf.addImage(canvas.toDataURL('image/jpeg', 0.92), 'JPEG', margin, y, width, height)
    y += height + gap
  }

  const pages = pdf.getNumberOfPages()
  for (let page = 1; page <= pages; page++) {
    pdf.setPage(page)
    pdf.setFontSize(8)
    pdf.setTextColor(120)
    pdf.text(`${brand.name}`, margin, pageHeight - margin + 2)
    pdf.text(`Page ${page} of ${pages}`, pageWidth - margin, pageHeight - margin + 2, {
      align: 'right',
    })
  }
  pdf.save(filename)
}

/** The header block at the top of printed exports. */
export const ExportHeader = ({ title, subtitle }: { title: string; subtitle?: string }) => (
  <div data-block style={{ padding: '4px 0 12px', borderBottom: '2px solid #111827' }}>
    <div style={{ fontSize: 12, color: '#6b7280' }}>{brand.name}</div>
    <div style={{ fontSize: 22, fontWeight: 700 }}>{title}</div>
    {subtitle && <div style={{ fontSize: 13, color: '#374151' }}>{subtitle}</div>}
    <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
      {new Date().toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}
    </div>
  </div>
)
