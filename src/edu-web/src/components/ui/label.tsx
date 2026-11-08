/**
 * The field label.
 *
 * Barely changed, and the restraint is the point: a label is read, not
 * interacted with, so the only thing asked of it is that it sits close
 * enough to its field to belong to it and is not mistaken for body text.
 *
 * Tracked out very slightly and set in the medium weight, which at 14px
 * separates it from the value underneath without resorting to uppercase.
 */

'use client'

import * as React from 'react'
import * as LabelPrimitive from '@radix-ui/react-label'

import { cn } from '@/lib/utils'

function Label({
  className,
  ...props
}: React.ComponentProps<typeof LabelPrimitive.Root>) {
  return (
    <LabelPrimitive.Root
      data-slot="label"
      className={cn(
        'flex items-center gap-2 text-sm leading-none font-medium tracking-[0.004em] select-none',
        'group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50',
        'peer-disabled:cursor-not-allowed peer-disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}

export { Label }
