// @vitest-environment jsdom
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Response } from '@/components/ai-elements/response'

afterEach(cleanup)

/**
 * The blinking cursor while an answer is written is pure CSS:
 *
 *   .is-typing > :is(p, h1..h6):last-child::after
 *   .is-typing > :is(ul, ol):last-child > li:last-child::after
 *
 * jsdom does not run ::after, so these pin the DOM shape that selector counts
 * on. The markdown renderer wraps code blocks and tables in its own <div>, so
 * only running text may carry the cursor; anything else would leave it
 * dangling on an empty line. If the renderer changes shape, these fail here
 * instead of looking broken in front of a student.
 */
const root = (markdown: string) => {
  const { container } = render(
    <Response className="is-typing">{markdown}</Response>,
  )
  const el = container.querySelector('.is-typing')
  expect(el, 'the class reaches a rendered element').not.toBeNull()
  return el as HTMLElement
}

describe('the cursor rides running text', () => {
  it('sits after the last paragraph', () => {
    const el = root('First paragraph.\n\nSecond paragraph.')
    expect([...el.children].map((c) => c.tagName)).toEqual(['P', 'P'])
    expect(el.lastElementChild?.textContent).toBe('Second paragraph.')
  })

  it('sits after the last item of a closing list', () => {
    const el = root('Steps:\n\n- Write the formula\n- Put in the values')
    const last = el.lastElementChild
    expect(last?.tagName).toBe('UL')
    expect(last?.lastElementChild?.tagName).toBe('LI')
    expect(last?.lastElementChild?.textContent).toBe('Put in the values')
  })

  it('sits after a formula, which the renderer keeps in a paragraph', () => {
    const el = root('Range:\n\n$$R = \\frac{v^2 \\sin 2\\theta}{g}$$')
    expect(el.lastElementChild?.tagName).toBe('P')
    expect(el.querySelector('.katex')).not.toBeNull()
  })
})

describe('the cursor stays away from blocks that are not text', () => {
  const notText = (el: HTMLElement) => {
    const last = el.lastElementChild
    expect(last).not.toBeNull()
    expect(
      ['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'UL', 'OL'],
      `${last?.tagName} must not be one the cursor attaches to`,
    ).not.toContain(last?.tagName)
  }

  it('a Python code block, which CS answers end with', () => {
    const el = root('In Python:\n\n```python\nprint(sum([1, 2]))\n```')
    expect(el.lastElementChild?.getAttribute('data-code-block-container')).toBe(
      'true',
    )
    notText(el)
  })

  it('a table', () => {
    const el = root('A table:\n\n| a | b |\n| - | - |\n| 1 | 2 |')
    expect(el.lastElementChild?.getAttribute('data-streamdown')).toBe(
      'table-wrapper',
    )
    notText(el)
  })

  it('a quote', () => {
    notText(root('> A quote at the end'))
  })
})

it('is absent once the answer is finished', () => {
  const { container } = render(<Response>Done.</Response>)
  expect(container.querySelector('.is-typing')).toBeNull()
})
