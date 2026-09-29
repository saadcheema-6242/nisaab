/**
 * Prepare AI-written text with formulas for Streamdown, which renders math
 * written as $$...$$ (inline or display):
 * - AI output sometimes doubles LaTeX backslashes (\\frac instead of \frac).
 *   In LaTeX \\ is a line break, so "\\cos\\theta" would show as "cos", "theta"
 *   on separate lines. A doubled backslash before a letter is made single.
 * - $...$, \(...\) and \[...\] become $$...$$. A single $ followed by a space
 *   (e.g. "$ 5") is left alone.
 * - Formulas written without any delimiters (e.g. "H = \frac{v^2}{2g}") are
 *   wrapped in $$...$$.
 * Code blocks and inline code are left untouched.
 */
const CODE = /(```[\s\S]*?```|`[^`\n]*`)/g

export const normalizeMath = (text: string): string =>
  text
    .split(CODE)
    .map((part, index) => (index % 2 === 1 ? part : normalizePart(part)))
    .join('')

const normalizePart = (text: string) =>
  wrapBareMath(toDoubleDollars(fixBackslashes(text)))

// Only before a letter, so a real line break such as "a \\ b" is kept
const fixBackslashes = (text: string) =>
  text.replace(/\\{2,}(?=[A-Za-z])/g, '\\')

const toDoubleDollars = (text: string) =>
  text
    .replace(
      /\\\[([\s\S]+?)\\\]/g,
      (_, math: string) => `\n$$\n${math.trim()}\n$$\n`,
    )
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, math: string) => `$$${math.trim()}$$`)
    .replace(
      /(?<![\\$])\$(?![$\s])([^$\n]+?)(?<![\\\s])\$(?!\$)/g,
      (_, math: string) => `$$${math}$$`,
    )

// A word that is certainly maths: a LaTeX command, or a sub/superscript (v_i, t^2)
const isStrong = (word: string) =>
  !word.includes('://') &&
  (/\\[A-Za-z]+/.test(word) || /[\^_][\w{\\]/.test(word))

// A word that can sit inside a formula: numbers, operators, single letters (R, g),
// or a number with a unit-like suffix (2g, 4H.)
const isWeak = (word: string) =>
  /^[\d.,:;()[\]{}+\-−×÷=*/<>≤≥|'°]+$/.test(word) ||
  /^[A-Za-z][.,:;)]?$/.test(word) ||
  /^\d+(\.\d+)?[A-Za-z]{1,2}[.,:;)]?$/.test(word)

// Markdown list, quote and heading markers stay outside the formula
const LINE_MARKER = /^(\s*(?:[-*+>]|#{1,6}|\d+[.)])\s+)/

const wrapLine = (line: string): string => {
  if (!/\\[A-Za-z]|[\^_]/.test(line)) return line
  const marker = LINE_MARKER.exec(line)?.[1] ?? ''
  // Words at even indexes, the whitespace between them at odd indexes
  const tokens = line.slice(marker.length).split(/(\s+)/)
  let result = marker
  let i = 0
  while (i < tokens.length) {
    const word = tokens[i]
    if (i % 2 === 1 || !word || !(isStrong(word) || isWeak(word))) {
      result += word
      i++
      continue
    }
    let end = i
    let strong = false
    for (let j = i; j < tokens.length; j += 2) {
      const next = tokens[j]
      if (!next || !(isStrong(next) || isWeak(next))) break
      strong ||= isStrong(next)
      end = j
    }
    const run = tokens.slice(i, end + 1).join('')
    result += strong ? `$$${run}$$` : run
    i = end + 1
  }
  return result
}

const wrapBareMath = (text: string) => {
  const parts = text.split('$$')
  // Unbalanced $$: leave the text as it is rather than guess
  if (parts.length % 2 === 0) return text
  return parts
    .map((part, index) =>
      index % 2 === 1 ? part : part.split('\n').map(wrapLine).join('\n'),
    )
    .join('$$')
}
