/**
 * Showing what a student attached to a post.
 *
 * Three shapes, because three things are wanted from them. A photo of a
 * worked question is looked at, so it shows inline. A voice note is listened
 * to, so it gets a player. Everything else is opened in another program, so
 * it gets a name, a size and a download.
 */

import {
  DownloadIcon,
  FileIcon,
  FileTextIcon,
  ImageIcon,
  Volume2Icon,
} from 'lucide-react'
import type { CommunityAttachment } from '@/data-acess/community'
import { Button } from '@/components/ui/button'

/** A size a person can judge a download by, before committing to it. */
export const readableSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** How long a voice note runs, as a clock reads. */
export const readableLength = (seconds: number | null): string => {
  if (!seconds || seconds < 0) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

const iconFor = (filename: string, kind: string) => {
  if (kind === 'image') return ImageIcon
  if (kind === 'audio') return Volume2Icon
  return filename.toLowerCase().endsWith('.pdf') ? FileTextIcon : FileIcon
}

const Unavailable = ({ filename }: { filename: string }) => (
  <div className="text-muted-foreground rounded-lg border border-dashed p-3 text-sm">
    {filename} could not be loaded.
  </div>
)

export const AttachmentView = ({ file }: { file: CommunityAttachment }) => {
  // A link that could not be signed leaves the attachment listed with no
  // URL. Saying so beats a broken image icon, which reads as the app
  // failing rather than one file being unavailable.
  if (!file.url) return <Unavailable filename={file.filename} />

  if (file.kind === 'image') {
    return (
      <a
        href={file.url}
        target="_blank"
        rel="noreferrer"
        className="block overflow-hidden rounded-lg border"
      >
        <img
          src={file.url}
          alt={file.filename}
          // Capped rather than natural size: a photo straight off a phone is
          // several thousand pixels tall and would push the whole thread off
          // the screen.
          className="max-h-96 w-full bg-muted object-contain"
          loading="lazy"
        />
      </a>
    )
  }

  if (file.kind === 'audio') {
    return (
      <div className="bg-muted/40 flex items-center gap-3 rounded-lg border p-3">
        <Volume2Icon className="text-muted-foreground size-4 shrink-0" />
        <audio controls preload="metadata" src={file.url} className="h-9 w-full">
          <track kind="captions" />
        </audio>
        {file.duration_seconds ? (
          <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
            {readableLength(file.duration_seconds)}
          </span>
        ) : null}
      </div>
    )
  }

  const Icon = iconFor(file.filename, file.kind)
  return (
    <div className="bg-muted/40 flex items-center gap-3 rounded-lg border p-3">
      <Icon className="text-muted-foreground size-5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{file.filename}</p>
        <p className="text-muted-foreground text-xs">
          {readableSize(file.size_bytes)}
        </p>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <a href={file.download_url || file.url} download={file.filename}>
          <DownloadIcon className="size-3.5" />
          <span className="sr-only sm:not-sr-only sm:ml-1.5">Download</span>
        </a>
      </Button>
    </div>
  )
}

export const AttachmentList = ({
  files,
}: {
  files: Array<CommunityAttachment>
}) => {
  if (files.length === 0) return null
  return (
    <div className="mt-3 space-y-2">
      {files.map((file) => (
        <AttachmentView key={file.id} file={file} />
      ))}
    </div>
  )
}
