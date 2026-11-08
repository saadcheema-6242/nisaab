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
  /** Override the toasts, for options that share a link rather than save a file. */
  pending?: string
  success?: string
  failure?: string
}

/** A "Download" button with a menu of export formats (PDF, PNG, ...). */
export const DownloadMenu = ({
  options,
  size = 'sm',
  variant = 'outline',
  iconOnly = false,
  autoOpen = false,
}: {
  options: ReadonlyArray<DownloadOption>
  size?: 'sm' | 'default'
  variant?: 'outline' | 'ghost'
  /** Just the icon, for tight rows like the practice history. */
  iconOnly?: boolean
  /** Open as soon as it appears, for a menu mounted by the click that asked for it. */
  autoOpen?: boolean
}) => {
  const [busy, setBusy] = useState(false)

  const run = async (option: DownloadOption) => {
    setBusy(true)
    const toastId = toast.loading(option.pending ?? 'Preparing your download…')
    try {
      await option.run()
      toast.success(option.success ?? 'Downloaded', { id: toastId })
    } catch (error) {
      console.error(error)
      toast.error(
        option.failure ?? 'Could not create the file, please try again',
        {
          id: toastId,
        },
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <DropdownMenu defaultOpen={autoOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          size={iconOnly ? 'icon' : size}
          variant={variant}
          disabled={busy}
          aria-label={iconOnly ? 'Download' : undefined}
        >
          {busy ? (
            <Loader2Icon className="size-4 animate-spin" />
          ) : (
            <DownloadIcon className="size-4" />
          )}
          {!iconOnly && 'Download'}
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
