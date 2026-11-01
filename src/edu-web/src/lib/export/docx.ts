/**
 * A small Word (.docx) writer.
 *
 * A .docx is a zip of XML parts, and jszip is already here for the flashcard
 * export, so this needs no new dependency. More to the point it writes real
 * text: the PDF exports rasterise the page, which is right for a paper that
 * will be printed and sat, and wrong for a plan a student wants to edit, paste
 * into a message or have read aloud.
 *
 * Only what a study plan needs is supported - headings, paragraphs, links and
 * a table. Anything richer belongs in a real library.
 */

/** One piece of a document, in the order it should appear. */
export type DocBlock =
  | { kind: 'heading'; text: string; level?: 1 | 2 | 3 }
  | { kind: 'paragraph'; text: string; italic?: boolean; muted?: boolean }
  | { kind: 'link'; text: string; url: string }
  | { kind: 'table'; head: ReadonlyArray<string>; rows: ReadonlyArray<ReadonlyArray<string>> }

/**
 * XML-escape, and drop the control characters XML cannot carry at all.
 *
 * Word refuses to open a file with a stray control character in it, and the
 * text here comes from a language model, so it cannot be assumed clean.
 */
const esc = (text: string) =>
  String(text ?? '')
    // eslint-disable-next-line no-control-regex
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

const HEADING_SIZES = { 1: 32, 2: 26, 3: 22 } as const
const GREEN = '15803D'
const GREY = '6B7280'

/** A run of text, with the formatting Word needs spelled out on it. */
const run = (
  text: string,
  { bold = false, italic = false, size = 20, color = '' } = {},
) => {
  // A newline inside <w:t> is not a line break in Word - it is whitespace, and
  // the lines run together. Each one has to become an explicit <w:br/>, which
  // is what makes a cell able to hold a step and its tasks.
  const lines = String(text ?? '').split('\n')
  const body = lines
    // xml:space keeps the leading and trailing spaces Word would otherwise trim
    .map((line) => `<w:t xml:space="preserve">${esc(line)}</w:t>`)
    .join('<w:br/>')
  return (
    `<w:r><w:rPr>${bold ? '<w:b/>' : ''}${italic ? '<w:i/>' : ''}` +
    `<w:sz w:val="${size}"/>${color ? `<w:color w:val="${color}"/>` : ''}</w:rPr>` +
    `${body}</w:r>`
  )
}

const para = (inner: string, { spaceAfter = 120 } = {}) =>
  `<w:p><w:pPr><w:spacing w:after="${spaceAfter}"/></w:pPr>${inner}</w:p>`

const cell = (text: string, { bold = false, width = 2000 } = {}) =>
  `<w:tc><w:tcPr><w:tcW w:w="${width}" w:type="dxa"/></w:tcPr>` +
  `${para(run(text, { bold, size: 18 }), { spaceAfter: 0 })}</w:tc>`

/** The body XML, plus any hyperlink relationships it referred to. */
const bodyFor = (blocks: ReadonlyArray<DocBlock>) => {
  const links: { id: string; url: string }[] = []
  const parts: string[] = []

  for (const block of blocks) {
    switch (block.kind) {
      case 'heading': {
        const level = block.level ?? 1
        parts.push(
          para(
            run(block.text, {
              bold: true,
              size: HEADING_SIZES[level],
              color: level === 1 ? GREEN : '',
            }),
            { spaceAfter: 160 },
          ),
        )
        break
      }
      case 'paragraph':
        parts.push(
          para(
            run(block.text, {
              italic: block.italic,
              color: block.muted ? GREY : '',
            }),
          ),
        )
        break
      case 'link': {
        const id = `rId${100 + links.length}`
        links.push({ id, url: block.url })
        parts.push(
          para(
            `<w:hyperlink r:id="${id}"><w:r><w:rPr><w:color w:val="1D4ED8"/>` +
              `<w:u w:val="single"/><w:sz w:val="20"/></w:rPr>` +
              `<w:t xml:space="preserve">${esc(block.text)}</w:t></w:r></w:hyperlink>`,
          ),
        )
        break
      }
      case 'table': {
        const widths = block.head.map((_, i) => (i === block.head.length - 1 ? 4200 : 1700))
        const header = `<w:tr>${block.head
          .map((text, i) => cell(text, { bold: true, width: widths[i] }))
          .join('')}</w:tr>`
        const rows = block.rows
          .map(
            (row) =>
              `<w:tr>${row.map((text, i) => cell(text, { width: widths[i] })).join('')}</w:tr>`,
          )
          .join('')
        parts.push(
          `<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/>` +
            `<w:tblW w:w="0" w:type="auto"/>` +
            `<w:tblBorders>` +
            ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']
              .map(
                (edge) =>
                  `<w:${edge} w:val="single" w:sz="4" w:space="0" w:color="D1D5DB"/>`,
              )
              .join('') +
            `</w:tblBorders></w:tblPr>${header}${rows}</w:tbl>` +
            para('', { spaceAfter: 160 }),
        )
        break
      }
    }
  }
  return { xml: parts.join(''), links }
}

/**
 * Build a .docx and hand it back as a Blob.
 *
 * `title` becomes the document's own title property, which is what a file
 * manager and a screen reader announce.
 */
export async function buildDocx(
  title: string,
  blocks: ReadonlyArray<DocBlock>,
): Promise<Blob> {
  const JSZip = (await import('jszip')).default
  const zip = new JSZip()
  // Word's own files carry no directory entries; jszip adds one per path
  // segment unless told otherwise, so stay close to what Word writes.
  const put = (path: string, xml: string) =>
    zip.file(path, xml, { createFolders: false })
  const { xml, links } = bodyFor(blocks)

  put(
    '[Content_Types].xml',
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
      `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
      `<Default Extension="xml" ContentType="application/xml"/>` +
      `<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>` +
      `<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>` +
      `</Types>`,
  )

  put(
    '_rels/.rels',
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>` +
      `<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>` +
      `</Relationships>`,
  )

  put(
    'docProps/core.xml',
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ` +
      `xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" ` +
      `xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">` +
      `<dc:title>${esc(title)}</dc:title>` +
      `<dcterms:created xsi:type="dcterms:W3CDTF">${new Date().toISOString()}</dcterms:created>` +
      `</cp:coreProperties>`,
  )

  put(
    'word/_rels/document.xml.rels',
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      links
        .map(
          (link) =>
            `<Relationship Id="${link.id}" ` +
            `Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" ` +
            `Target="${esc(link.url)}" TargetMode="External"/>`,
        )
        .join('') +
      `</Relationships>`,
  )

  put(
    'word/document.xml',
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ` +
      `xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
      `<w:body>${xml}` +
      // A4 with sane margins; without a sectPr Word picks US Letter
      `<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>` +
      `<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>` +
      `</w:body></w:document>`,
  )

  return zip.generateAsync({
    type: 'blob',
    mimeType:
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  })
}

/** Save a blob under a filename, the way the other exports do. */
export const saveBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  // Revoked on the next turn: revoking immediately cancels the download in Safari
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}
