// @vitest-environment jsdom
import JSZip from 'jszip'
import { describe, expect, it } from 'vitest'
import { buildDocx, type DocBlock } from './docx'

/**
 * A .docx is a zip of XML parts, and Word refuses the whole file over one
 * malformed part — so these check the structure and the XML rather than
 * trusting it. The content comes from a language model, which means quotes,
 * ampersands and the occasional control character.
 */

const BLOCKS: DocBlock[] = [
  { kind: 'heading', text: 'Study plan', level: 1 },
  { kind: 'heading', text: 'Day 1', level: 2 },
  { kind: 'paragraph', text: 'You are getting Newton & momentum wrong.' },
  { kind: 'paragraph', text: 'Keep going', italic: true, muted: true },
  {
    kind: 'table',
    head: ['Outcome', 'What', 'Time', 'To do'],
    rows: [
      ['P-11-B-05', 'Quiz', '20 min', 'Apply F = ma — Target: Score 70% or more'],
      ['P-11-B-06', 'Read', '15 min', 'Air resistance <qualitatively>'],
    ],
  },
  { kind: 'link', text: 'Open this plan', url: 'https://example.com/p/1?a=2&b=3' },
]

// jsdom's Blob has no arrayBuffer(), so read it the way a browser always could
const bytes = (blob: Blob) =>
  new Promise<ArrayBuffer>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as ArrayBuffer)
    reader.onerror = () => reject(reader.error)
    reader.readAsArrayBuffer(blob)
  })

const open = async (blocks: DocBlock[] = BLOCKS) => {
  const blob = await buildDocx('Study plan', blocks)
  return JSZip.loadAsync(await bytes(blob))
}

const parse = (xml: string) => {
  const doc = new DOMParser().parseFromString(xml, 'application/xml')
  const error = doc.querySelector('parsererror')
  return { doc, error: error?.textContent ?? null }
}

describe('buildDocx', () => {
  it('writes every part Word needs to open the file', async () => {
    const zip = await open()
    for (const part of [
      '[Content_Types].xml',
      '_rels/.rels',
      'word/document.xml',
      'word/_rels/document.xml.rels',
      'docProps/core.xml',
    ]) {
      expect(zip.file(part), `missing ${part}`).not.toBeNull()
    }
  })

  it('writes XML that parses, in every part', async () => {
    const zip = await open()
    const names = Object.keys(zip.files).filter((name) => !zip.files[name].dir)
    expect(names.length).toBeGreaterThanOrEqual(5)
    for (const name of names) {
      const xml = await zip.file(name)!.async('string')
      const { error } = parse(xml)
      expect(error, `${name} is malformed: ${error}`).toBeNull()
    }
  })

  it('escapes the characters that would break the XML', async () => {
    const zip = await open()
    const xml = await zip.file('word/document.xml')!.async('string')
    // The ampersand and angle brackets must survive as text, not as markup
    expect(xml).toContain('Newton &amp; momentum')
    expect(xml).toContain('&lt;qualitatively&gt;')
    expect(parse(xml).error).toBeNull()
  })

  it('strips control characters rather than producing a file Word rejects', async () => {
    const zip = await open([
      { kind: 'paragraph', text: 'bad\u0007char\u001Fhere' },
    ])
    const xml = await zip.file('word/document.xml')!.async('string')
    expect(xml).toContain('badcharhere')
    expect(parse(xml).error).toBeNull()
  })

  it('declares the main document part in the content types', async () => {
    const zip = await open()
    const types = await zip.file('[Content_Types].xml')!.async('string')
    expect(types).toContain('/word/document.xml')
    expect(types).toContain('wordprocessingml.document.main+xml')
  })

  it('gives every hyperlink a relationship that actually exists', async () => {
    const zip = await open()
    const body = await zip.file('word/document.xml')!.async('string')
    const rels = await zip.file('word/_rels/document.xml.rels')!.async('string')

    const used = [...body.matchAll(/r:id="([^"]+)"/g)].map((m) => m[1])
    expect(used.length).toBe(1)
    for (const id of used) {
      expect(rels, `no relationship for ${id}`).toContain(`Id="${id}"`)
    }
    // A link out of the document must say so, or Word treats it as internal
    expect(rels).toContain('TargetMode="External"')
    expect(rels).toContain('a=2&amp;b=3')
  })

  it('keeps the table rows and their cells', async () => {
    const zip = await open()
    const xml = await zip.file('word/document.xml')!.async('string')
    const { doc } = parse(xml)
    const rows = doc.getElementsByTagName('w:tr')
    expect(rows.length).toBe(3) // one header, two steps
    expect(xml).toContain('P-11-B-05')
    expect(xml).toContain('Score 70% or more')
  })

  it('turns a newline into a real line break, not run-together text', async () => {
    const zip = await open([
      { kind: 'paragraph', text: 'first line\nsecond line' },
    ])
    const xml = await zip.file('word/document.xml')!.async('string')
    expect(xml).toContain('<w:br/>')
    expect(xml).toContain('first line')
    expect(xml).toContain('second line')
    // and they must be separate runs of text, not one joined string
    expect(xml).not.toContain('first linesecond line')
    expect(parse(xml).error).toBeNull()
  })

  it('sets A4, so the plan does not print on US Letter', async () => {
    const zip = await open()
    const xml = await zip.file('word/document.xml')!.async('string')
    expect(xml).toContain('w:w="11906"')
    expect(xml).toContain('w:h="16838"')
  })

  it('carries the document title for the file manager to show', async () => {
    const zip = await open()
    const core = await zip.file('docProps/core.xml')!.async('string')
    expect(core).toContain('<dc:title>Study plan</dc:title>')
  })

  it('produces a file even with nothing in it', async () => {
    const zip = await open([])
    const xml = await zip.file('word/document.xml')!.async('string')
    expect(parse(xml).error).toBeNull()
    expect(xml).toContain('<w:body>')
  })
})
