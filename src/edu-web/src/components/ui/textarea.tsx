/**
 * The multi-line field. Styled from the same recipe as Input, deliberately.
 *
 * A form where the single-line fields are recessed and the message box is
 * transparent looks like two people built it. Everything here mirrors
 * input.tsx; if one changes, the other has to.
 */

import * as React from 'react'

import { cn } from '@/lib/utils'

function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'border-input flex field-sizing-content min-h-16 w-full rounded-md border px-3 py-2',
        'text-base md:text-sm',
        'caret-primary placeholder:text-muted-foreground/80',
        'selection:bg-primary selection:text-primary-foreground',
        'bg-muted/40 shadow-[inset_0_1px_2px_0_rgb(16_38_30/0.05)] dark:bg-input/30',
        'transition-[color,box-shadow,background-color,border-color] duration-150 ease-out',
        'outline-none',
        'hover:border-ring/45',
        'focus-visible:bg-card focus-visible:border-ring focus-visible:ring-ring/45 focus-visible:ring-[3px] focus-visible:shadow-none',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40',
        'motion-reduce:transition-none',
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }
