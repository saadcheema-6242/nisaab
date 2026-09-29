import type { SloDto } from '@/integrations/api/client'

export const cognitiveLevelNames = {
  K: 'Knowledge',
  U: 'Understanding',
  A: 'Application',
} as const

export const assessmentForms: Record<
  SloDto['assessment_form'],
  { label: string; detail: string }
> = {
  summative: {
    label: 'Examined',
    detail: 'Can be asked in the annual exam paper.',
  },
  formative: {
    label: 'Not examined',
    detail: 'Classroom or lab learning only; not asked in the annual exam.',
  },
  practical: {
    label: 'Practical',
    detail: 'Assessed in the practical exam (lab work), not the theory paper.',
  },
  unknown: { label: 'Unclassified', detail: 'Assessment form not listed.' },
}

export type MasteryLevel = 'none' | 'weak' | 'developing' | 'strong'

export const masteryLevel = (mastery?: number | null): MasteryLevel => {
  if (mastery === null || mastery === undefined) return 'none'
  if (mastery < 0.5) return 'weak'
  if (mastery < 0.8) return 'developing'
  return 'strong'
}

export const masteryStyles: Record<
  MasteryLevel,
  { dot: string; bar: string; label: string }
> = {
  none: { dot: 'bg-muted-foreground/25', bar: 'bg-muted', label: 'Not practised' },
  weak: { dot: 'bg-red-500', bar: 'bg-red-500', label: 'Needs work' },
  developing: { dot: 'bg-amber-500', bar: 'bg-amber-500', label: 'Getting there' },
  strong: { dot: 'bg-emerald-500', bar: 'bg-emerald-500', label: 'Strong' },
}
