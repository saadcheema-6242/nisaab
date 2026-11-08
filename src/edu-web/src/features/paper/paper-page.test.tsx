// @vitest-environment jsdom
import { Atom, Result } from '@effect-atom/atom-react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Effect } from 'effect'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { countQuestions, formatMarks, sectionMarks } from './paper-utils'
import type { ReactNode } from 'react'
import type { PaperDto } from '@/integrations/api/client'

const papers = vi.hoisted(() => new Map<string, unknown>())

vi.mock('@/data-acess/paper', () => ({
  paperAtom: (key: string) => papers.get(key),
  savePaperAnswersAtom: Atom.fn(() => Effect.void),
  submitPaperAtom: Atom.fn(() => Effect.void),
}))
vi.mock('@tanstack/react-router', () => ({
  Link: ({ children }: { children: ReactNode }) => <a>{children}</a>,
}))
vi.mock('@/components/ui/sidebar', () => ({ SidebarTrigger: () => null }))
vi.mock('@/components/math-text', () => ({
  MathText: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

const { PaperPage } = await import('./paper-page')

const mcq = (id: string, extra: object = {}) => ({
  id,
  type: 'mcq',
  marks: 0.5,
  question: `Question ${id}`,
  options: { a: 'one', b: 'two', c: 'three', d: 'four' },
  ...extra,
})
const written = (id: string, choice: string) => ({
  id,
  type: 'srq',
  marks: 4,
  question: `Short question ${id}`,
  choice_group: 'B1',
  choice,
})

const halfPaper = (status: string, result?: object) =>
  ({
    id: 'p1',
    project_id: 'proj',
    title: 'Physics XI FBISE half paper (new pattern): whole syllabus',
    length: 'half',
    time_limit_minutes: 90,
    total_marks: 6,
    status,
    answers: {},
    sections:
      status === 'preparing'
        ? []
        : [
            {
              id: 'A',
              title: 'Section A: Multiple choice questions',
              items: [
                mcq('m1'),
                mcq('m2'),
                mcq('m3', {
                  stimulus: 'A ball is thrown at 20 m/s.',
                  group: 's1',
                }),
                mcq('m4', {
                  stimulus: 'A ball is thrown at 20 m/s.',
                  group: 's1',
                }),
              ],
            },
            {
              id: 'B',
              title: 'Section B: Short questions (answer (a) OR (b) in each)',
              items: [written('q1', 'a'), written('q2', 'b')],
            },
          ],
    result,
  }) as unknown as PaperDto

const show = (paper: PaperDto) => {
  papers.set('proj:p1', Atom.make(Result.success(paper)))
  render(<PaperPage projectId="proj" paperId="p1" />)
}

afterEach(() => {
  cleanup()
  localStorage.clear()
})

describe('paper utils', () => {
  it('counts a choice pair once', () => {
    const paper = halfPaper('ready')
    expect(countQuestions(paper)).toBe(5)
    expect(sectionMarks(paper.sections[1])).toBe(4)
    expect(formatMarks(0.1 + 0.2)).toBe('0.3')
  })
})

describe('PaperPage', () => {
  it('waits while a board paper is being set', () => {
    show(halfPaper('preparing'))
    expect(screen.getByText('Setting your paper…')).toBeTruthy()
  })

  it('shows stimulus sets and an (a) OR (b) choice', () => {
    show(halfPaper('ready'))
    fireEvent.click(screen.getByText('Start paper'))
    expect(
      screen.getByText('Read the following and answer questions 3 to 4.'),
    ).toBeTruthy()
    expect(screen.getByText('A ball is thrown at 20 m/s.')).toBeTruthy()
    expect(screen.getByText('Answer either (a) or (b)')).toBeTruthy()
    expect(screen.getByText('0/5 answered')).toBeTruthy()

    fireEvent.click(screen.getByText('Short question q2'))
    const answer = screen.getByPlaceholderText(/Write your answer to \(b\)/)
    fireEvent.change(answer, { target: { value: 'F = ma' } })
    expect(screen.getByText('1/5 answered')).toBeTruthy()
  })

  it('marks the answered choice and offers the other one', () => {
    show(
      halfPaper('submitted', {
        score: 3.5,
        max_score: 6,
        percent: 58,
        grade: 'C',
        descriptor: 'Fair',
        sections: [
          { id: 'A', title: 'Section A', score: 1, max_score: 2 },
          { id: 'B', title: 'Section B', score: 2.5, max_score: 4 },
        ],
        items: [
          {
            id: 'm1',
            type: 'mcq',
            marks: 0.5,
            awarded: 0.5,
            chosen: 'a',
            correct_option: 'a',
          },
          {
            id: 'q1',
            type: 'srq',
            marks: 4,
            awarded: 0,
            model_answer: 'Model (a)',
          },
          {
            id: 'q2',
            type: 'srq',
            marks: 4,
            awarded: 2.5,
            answer: 'F = ma',
            model_answer: 'Model (b)',
          },
        ],
      }),
    )
    expect(screen.getByText('3.5/6')).toBeTruthy()
    // Section B's total and the answered question (b)
    expect(screen.getAllByText('2.5/4')).toHaveLength(2)
    expect(screen.getByText('5 (b).')).toBeTruthy()
    expect(
      screen.getByText('See the other choice (a) and its model answer'),
    ).toBeTruthy()
  })
})
