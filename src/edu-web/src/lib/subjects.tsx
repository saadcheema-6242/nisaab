import {
  AtomIcon,
  CodeIcon,
  DnaIcon,
  FlaskConicalIcon,
  FolderIcon,
  SigmaIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const subjects = {
  PHY: {
    icon: AtomIcon,
    className: 'bg-sky-500/10 text-sky-600 dark:text-sky-400',
  },
  CHEM: {
    icon: FlaskConicalIcon,
    className: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  },
  BIO: {
    icon: DnaIcon,
    className: 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
  },
  MATH: {
    icon: SigmaIcon,
    className: 'bg-violet-500/10 text-violet-600 dark:text-violet-400',
  },
  CS: {
    icon: CodeIcon,
    className: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  },
} as const

export const SubjectIcon = ({
  code,
  className,
}: {
  code?: string | null
  className?: string
}) => {
  const subject = code ? subjects[code as keyof typeof subjects] : undefined
  const Icon = subject?.icon ?? FolderIcon
  return (
    <span
      className={cn(
        'flex size-9 shrink-0 items-center justify-center rounded-lg',
        subject?.className ?? 'bg-muted text-muted-foreground',
        className,
      )}
    >
      <Icon className="size-5" />
    </span>
  )
}

export const groups = [
  {
    code: 'PRE_MED',
    name: 'Pre-Medical',
    subjects: 'Physics, Chemistry, Biology',
  },
  {
    code: 'PRE_ENG',
    name: 'Pre-Engineering',
    subjects: 'Physics, Chemistry, Mathematics',
  },
  {
    code: 'ICS',
    name: 'ICS (Computer Science)',
    subjects: 'Physics, Mathematics, Computer Science',
  },
] as const

export const grades = [
  { grade: 11, name: 'Class XI', detail: 'HSSC-I · 1st year' },
  { grade: 12, name: 'Class XII', detail: 'HSSC-II · 2nd year' },
] as const

export const groupName = (code: string) =>
  groups.find((g) => g.code === code)?.name ?? code

export const gradeName = (grade: number) =>
  grades.find((g) => g.grade === grade)?.name ?? `Class ${grade}`
