// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ThinkingIndicator } from './thinking-indicator'
import { ThinkingDots } from '@/components/ui/thinking-dots'

afterEach(cleanup)

describe('ThinkingDots', () => {
  it('draws three dots', () => {
    const { container } = render(<ThinkingDots />)
    expect(container.querySelectorAll('.thinking-dot')).toHaveLength(3)
  })

  it('staggers them, so they travel rather than blink together', () => {
    const { container } = render(<ThinkingDots />)
    const delays = [
      ...container.querySelectorAll<HTMLElement>('.thinking-dot'),
    ].map((dot) => dot.style.animationDelay)
    expect(delays).toEqual(['0ms', '150ms', '300ms'])
  })

  it('says what is happening for a screen reader, which sees no animation', () => {
    render(<ThinkingDots label="Checking the FBISE syllabus" />)
    expect(screen.getByRole('status')).toBeDefined()
    expect(screen.getByLabelText('Checking the FBISE syllabus')).toBeDefined()
  })
})

describe('ThinkingIndicator', () => {
  it('shows the dots and the line saying what the tutor is doing', () => {
    const { container } = render(
      <ThinkingIndicator lang="en" label="Thinking…" />,
    )
    expect(container.querySelectorAll('.thinking-dot')).toHaveLength(3)
    expect(screen.getByText('Thinking…')).toBeDefined()
  })

  it('reads right-to-left for Urdu without a separate component', () => {
    const { container } = render(
      <ThinkingIndicator lang="ur" label="سوچ رہا ہے" />,
    )
    expect(container.querySelector('[dir="auto"]')).not.toBeNull()
  })
})
