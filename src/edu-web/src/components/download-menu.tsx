import { DownloadIcon, Loader2Icon } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export type DownloadOption = {
  label: string
  run: () => Promise<void>
}

/** A "Download" button with a menu of export formats (PDF, PNG, ...). */
export const DownloadMenu = ({
  options,
  size = 'sm',
  variant = 'outline',
}: {
  options: ReadonlyArray<DownloadOption>
  size?: 'sm' | 'default'
  variant?: 'outline' | 'ghost'
}) => {
  const [busy, setBusy] = useState(false)

  const run = async (option: DownloadOption) => {
    setBusy(true)
    const toastId = toast.loading('Preparing your download…')
    try {
      await option.run()
      toast.success('Downloaded', { id: toastId })
    } catch (error) {
      console.error(error)
      toast.error('Could not create the file, please try again', { id: toastId })
    } finally {
      setBusy(false)
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button size={size} variant={variant} disabled={busy}>
          {busy ? (
            <Loader2Icon className="size-4 animate-spin" />
          ) : (
            <DownloadIcon className="size-4" />
          )}
          Download
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {options.map((option) => (
          <DropdownMenuItem key={option.label} onSelect={() => run(option)}>
            {option.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
