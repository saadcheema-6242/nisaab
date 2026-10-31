// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { CognitiveBadge } from './cognitive-badge'

afterEach(cleanup)

describe('CognitiveBadge', () => {
  it('shows the letter for each level', () => {
    for (const level of ['K', 'U', 'A']) {
      const { unmount } = render(<CognitiveBadge level={level} />)
      expect(screen.getByText(level)).toBeDefined()
      unmount()
    }
  })

  it('is green, so the level reads as information about the question', () => {
    render(<CognitiveBadge level="K" />)
    const badge = screen.getByText('K')
    expect(badge.className).toContain('text-emerald-700')
    expect(badge.className).toContain('dark:text-emerald-400')
    expect(badge.className).toContain('bg-emerald-500/15')
  })

  it('spells the level out when asked, and names it for a screen reader', () => {
    render(<CognitiveBadge level="A" showName />)
    expect(screen.getByText('Application')).toBeDefined()
    expect(screen.getByTitle('Application question')).toBeDefined()
  })

  it('is just the letter by default', () => {
    render(<CognitiveBadge level="U" />)
    expect(screen.queryByText('Understanding')).toBeNull()
  })

  it('accepts a level in any case, with spaces', () => {
    render(<CognitiveBadge level=" u " />)
    expect(screen.getByText('U')).toBeDefined()
  })

  it('renders nothing when the level is missing or not a level', () => {
    // A question written before the level was recorded, or a model that
    // answered with something else: the badge must not invent one.
    for (const level of [null, undefined, '', 'X', 'Knowledge']) {
      const { container, unmount } = render(<CognitiveBadge level={level} />)
      expect(container.innerHTML).toBe('')
      unmount()
    }
  })
})
