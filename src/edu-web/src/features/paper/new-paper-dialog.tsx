import { useAtomSet } from '@effect-atom/atom-react'
import { useNavigate } from '@tanstack/react-router'
import { FileTextIcon, Loader2Icon } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import type { DomainDto } from '@/integrations/api/client'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { createPaperAtom } from '@/data-acess/paper'
import { cn } from '@/lib/utils'

const WHOLE = 'all'
const lengths = [
  {
    value: 'mini',
    label: 'Mini',
    detail: '8 MCQs + 2 short questions · 20 min',
  },
  {
    value: 'standard',
    label: 'Standard',
    detail: '12 MCQs + 4 short + 1 long question · 45 min',
  },
  {
    value: 'half',
    label: 'Half board paper (new pattern)',
    detail: 'Stimulus MCQs + short and long questions with (a) OR (b) · 90 min',
  },
  {
    value: 'board',
    label: 'Full board paper (new pattern)',
    detail: 'The complete FBISE paper: Sections A, B and C · 3 hours',
  },
] as const

type Length = (typeof lengths)[number]['value']

/** Choose length and scope, then open a new practice paper. */
export const NewPaperDialog = ({
  projectId,
  domains,
}: {
  projectId: string
  domains: ReadonlyArray<DomainDto>
}) => {
  const navigate = useNavigate()
  const createPaper = useAtomSet(createPaperAtom, { mode: 'promise' })
  const [open, setOpen] = useState(false)
  const [length, setLength] = useState<Length>('mini')
  const [scope, setScope] = useState(WHOLE)
  const [busy, setBusy] = useState(false)

  const handleCreate = async () => {
    setBusy(true)
    try {
      const paper = await createPaper({
        projectId,
        length,
        topic: scope === WHOLE ? undefined : scope,
      })
      setOpen(false)
      navigate({
        to: '/dashboard/p/$projectId/paper/$paperId',
        params: { projectId, paperId: paper.id },
      })
    } catch {
      toast.error('Could not make the paper, please try again')
    } finally {
      setBusy(false)
    }
  }

  const examined = domains.filter((d) => d.examined_count > 0)

  return (
    <Dialog open={open} onOpenChange={(value) => !busy && setOpen(value)}>
      <DialogTrigger asChild>
        <Button size="sm">
          <FileTextIcon className="size-4" />
          Practice paper
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New practice paper</DialogTitle>
          <DialogDescription>
            FBISE-style questions from the examined SLOs, marked like an
            examiner. Board papers follow FBISE's new pattern (50% MCQs) and
            take a minute or two to set.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-2">
            {lengths.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setLength(option.value)}
                className={cn(
                  'rounded-lg border p-3 text-left transition-colors hover:bg-accent/50',
                  length === option.value &&
                    'border-primary bg-primary/5 ring-1 ring-primary',
                )}
              >
                <div className="font-medium">{option.label}</div>
                <div className="text-sm text-muted-foreground">
                  {option.detail}
                </div>
              </button>
            ))}
          </div>
          <Select value={scope} onValueChange={setScope}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={WHOLE}>Whole syllabus</SelectItem>
              {examined.map((domain) => (
                <SelectItem key={domain.code} value={domain.name}>
                  {domain.code} · {domain.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <DialogFooter>
          <Button onClick={handleCreate} disabled={busy}>
            {busy && <Loader2Icon className="size-4 animate-spin" />}
            {busy ? 'Preparing your paper…' : 'Make paper'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
