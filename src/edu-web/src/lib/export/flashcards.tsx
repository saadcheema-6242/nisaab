import {
  BRAND,
  fileSlug,
  fontsFor,
  renderOffscreen,
  saveBlob,
  toCanvas,
} from './core'
import type { FlashcardDto } from '@/integrations/api/client'
import { MathText } from '@/components/math-text'
import { brand } from '@/lib/brand'

// --- Printable cards: 8 per A4 page, fronts then backs ---

const CARD_MM = { width: 88, height: 60, gap: 6 }
const CARD_PX = { width: 333, height: 227 } // 88 x 60 mm at 96 dpi

const PrintFace = ({
  label,
  text,
  number,
}: {
  label: string
  text: string
  number: number
}) => (
  <div
    data-face
    style={{
      width: CARD_PX.width,
      height: CARD_PX.height,
      boxSizing: 'border-box',
      border: '1px dashed #9ca3af',
      padding: 14,
      display: 'flex',
      flexDirection: 'column',
      fontSize: 13,
      overflow: 'hidden',
    }}
  >
    <div style={{ fontSize: 9, color: '#6b7280', display: 'flex', justifyContent: 'space-between' }}>
      <span>{label}</span>
      <span>#{number}</span>
    </div>
    <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
      <MathText>{text}</MathText>
    </div>
  </div>
)

export async function exportFlashcardsPdf(title: string, cards: ReadonlyArray<FlashcardDto>) {
  const { element, cleanup } = await renderOffscreen(
    <div>
      {cards.map((card, i) => (
        <div key={card.id}>
          <PrintFace label="Question" text={card.question} number={i + 1} />
          <PrintFace label="Answer" text={card.answer} number={i + 1} />
        </div>
      ))}
    </div>,
    CARD_PX.width,
  )
  try {
    const faces = Array.from(element.querySelectorAll<HTMLElement>('[data-face]'))
    const fronts = faces.filter((_, i) => i % 2 === 0)
    const backs = faces.filter((_, i) => i % 2 === 1)
    const { jsPDF } = await import('jspdf')
    const pdf = new jsPDF({ unit: 'mm', format: 'a4' })
    const fontCss = await fontsFor(element)
    const left = (210 - CARD_MM.width * 2 - CARD_MM.gap) / 2
    const top = (297 - CARD_MM.height * 4 - CARD_MM.gap * 3) / 2
    const perPage = 8
    let firstPage = true
    for (let start = 0; start < cards.length; start += perPage) {
      // A page of fronts, then the backs mirrored left-right for double-sided printing
      for (const side of ['front', 'back'] as const) {
        if (!firstPage) pdf.addPage()
        firstPage = false
        const list = side === 'front' ? fronts : backs
        for (let i = start; i < Math.min(start + perPage, cards.length); i++) {
          const slot = i - start
          const row = Math.floor(slot / 2)
          const col = side === 'front' ? slot % 2 : 1 - (slot % 2)
          const canvas = await toCanvas(list[i], 3, fontCss)
          pdf.addImage(
            canvas.toDataURL('image/jpeg', 0.92),
            'JPEG',
            left + col * (CARD_MM.width + CARD_MM.gap),
            top + row * (CARD_MM.height + CARD_MM.gap),
            CARD_MM.width,
            CARD_MM.height,
          )
        }
        pdf.setFontSize(8)
        pdf.setTextColor(120)
        pdf.text(
          `${brand.name} · ${title} · ${side === 'front' ? 'Questions' : 'Answers (print on the back)'}`,
          left,
          top - 4,
        )
      }
    }
    pdf.save(`${fileSlug(title)}-cards.pdf`)
  } finally {
    cleanup()
  }
}

// --- Share images: one square card per flashcard ---

const ShareCard = ({
  card,
  number,
  total,
  title,
  sloCode,
}: {
  card: FlashcardDto
  number: number
  total: number
  title: string
  sloCode?: string | null
}) => (
  <div
    data-share
    style={{
      width: 1080,
      height: 1080,
      boxSizing: 'border-box',
      display: 'flex',
      flexDirection: 'column',
      background: '#ffffff',
    }}
  >
    <div
      style={{
        background: `linear-gradient(135deg, ${BRAND.green}, ${BRAND.soft})`,
        color: '#ffffff',
        padding: '44px 64px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <div>
        <div style={{ fontSize: 40, fontWeight: 800 }}>{brand.name}</div>
        <div style={{ fontSize: 26, opacity: 0.9 }}>{title}</div>
      </div>
      <div style={{ textAlign: 'right', fontSize: 26 }}>
        {sloCode && <div style={{ fontFamily: 'monospace', fontWeight: 700 }}>{sloCode}</div>}
        <div style={{ opacity: 0.85 }}>
          Card {number} / {total}
        </div>
      </div>
    </div>
    <div style={{ flex: 1, padding: '48px 64px', display: 'flex', flexDirection: 'column', gap: 36 }}>
      <div>
        <div style={{ fontSize: 24, color: BRAND.green, fontWeight: 700, marginBottom: 12 }}>QUESTION</div>
        <div style={{ fontSize: 40, fontWeight: 600, lineHeight: 1.35 }}>
          <MathText>{card.question}</MathText>
        </div>
      </div>
      <div style={{ height: 3, background: '#e5e7eb' }} />
      <div>
        <div style={{ fontSize: 24, color: BRAND.soft, fontWeight: 700, marginBottom: 12 }}>ANSWER</div>
        <div style={{ fontSize: 34, lineHeight: 1.4, color: '#1f2937' }}>
          <MathText>{card.answer}</MathText>
        </div>
      </div>
    </div>
    <div style={{ padding: '0 64px 36px', fontSize: 22, color: '#9ca3af' }}>
      FBISE FSc revision · {brand.name}
    </div>
  </div>
)

export async function shareImages(
  title: string,
  cards: ReadonlyArray<FlashcardDto>,
  sloCode?: string | null,
) {
  const { element, cleanup } = await renderOffscreen(
    <div>
      {cards.map((card, i) => (
        <ShareCard
          key={card.id}
          card={card}
          number={i + 1}
          total={cards.length}
          title={title}
          sloCode={sloCode}
        />
      ))}
    </div>,
    1080,
  )
  try {
    const nodes = Array.from(element.querySelectorAll<HTMLElement>('[data-share]'))
    const fontCss = await fontsFor(element)
    const blobs: Array<Blob> = []
    for (const node of nodes) {
      const canvas = await toCanvas(node, 1, fontCss)
      blobs.push(await new Promise<Blob>((resolve, reject) =>
        canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('Image failed'))), 'image/png'),
      ))
    }
    return blobs
  } finally {
    cleanup()
  }
}

export async function exportFlashcardImage(
  title: string,
  cards: ReadonlyArray<FlashcardDto>,
  index: number,
  sloCode?: string | null,
) {
  const [blob] = await shareImages(title, [cards[index]], sloCode)
  saveBlob(blob, `${fileSlug(title)}-card-${index + 1}.png`)
}

export async function exportFlashcardImagesZip(
  title: string,
  cards: ReadonlyArray<FlashcardDto>,
  sloCode?: string | null,
) {
  const blobs = await shareImages(title, cards, sloCode)
  const { default: JSZip } = await import('jszip')
  const zip = new JSZip()
  blobs.forEach((blob, i) => zip.file(`${fileSlug(title)}-card-${i + 1}.png`, blob))
  saveBlob(await zip.generateAsync({ type: 'blob' }), `${fileSlug(title)}-cards.zip`)
}
