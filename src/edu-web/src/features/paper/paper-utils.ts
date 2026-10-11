import type { PaperDto, PaperItemDto, PaperSectionDto } from '@/integrations/api/client'

/** Marks without float noise: 0.5, 23.75, 42. */
export const formatMarks = (n: number) => String(Math.round(n * 100) / 100)

/** Section A stimulus sets and the (a) OR (b) pairs of Sections B and C. */
export type PaperBlock =
  | { kind: 'single'; item: PaperItemDto }
  | { kind: 'stimulus'; group: string; stimulus: string; items: Array<PaperItemDto> }
  | { kind: 'choice'; group: string; items: Array<PaperItemDto> }

export const sectionBlocks = (section: PaperSectionDto): Array<PaperBlock> => {
  const blocks: Array<PaperBlock> = []
  for (const item of section.items) {
    const last = blocks.at(-1)
    if (item.choice_group) {
      if (last?.kind === 'choice' && last.group === item.choice_group) last.items.push(item)
      else blocks.push({ kind: 'choice', group: item.choice_group, items: [item] })
    } else if (item.group && item.stimulus) {
      if (last?.kind === 'stimulus' && last.group === item.group) last.items.push(item)
      else blocks.push({ kind: 'stimulus', group: item.group, stimulus: item.stimulus, items: [item] })
    } else {
      blocks.push({ kind: 'single', item })
    }
  }
  return blocks
}

/** Questions the student answers: a choice pair counts once. */
export const sectionQuestions = (section: PaperSectionDto) =>
  sectionBlocks(section).reduce(
    (n, block) => n + (block.kind === 'stimulus' ? block.items.length : 1),
    0,
  )

/** Marks available: a choice pair counts once. */
export const sectionMarks = (section: PaperSectionDto) =>
  sectionBlocks(section).reduce(
    (n, block) =>
      n +
      (block.kind === 'single'
        ? block.item.marks
        : block.kind === 'choice'
          ? Math.max(...block.items.map((i) => i.marks))
          : block.items.reduce((m, i) => m + i.marks, 0)),
    0,
  )

export const countQuestions = (paper: PaperDto) =>
  paper.sections.reduce((n, s) => n + sectionQuestions(s), 0)

export const hasChoices = (paper: PaperDto) =>
  paper.sections.some((s) => s.items.some((i) => i.choice_group))
