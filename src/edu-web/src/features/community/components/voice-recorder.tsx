/**
 * Recording a voice note in the browser.
 *
 * Explaining a derivation out loud is faster than typing it, and a student
 * who will not write three paragraphs will happily talk for forty seconds.
 *
 * The microphone is asked for only when the button is pressed, never on page
 * load, and the track is stopped the moment recording ends. A browser tab
 * showing a recording indicator after the student thought they had finished
 * is the kind of thing that gets an app uninstalled.
 */

import { useEffect, useRef, useState } from 'react'
import { MicIcon, SquareIcon, Trash2Icon } from 'lucide-react'
import { readableLength } from './attachment-view'
import { Button } from '@/components/ui/button'

/** Longer than this is a lecture, and nobody listens to the end of it. */
const MAX_SECONDS = 300

/** The first type this browser can actually record. */
const pickType = (): string | undefined => {
  if (typeof MediaRecorder === 'undefined') return undefined
  for (const type of [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
  ]) {
    if (MediaRecorder.isTypeSupported(type)) return type
  }
  return undefined
}

export const VoiceRecorder = ({
  onRecorded,
  disabled,
}: {
  onRecorded: (file: File, seconds: number) => void
  disabled?: boolean
}) => {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const recorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Array<Blob>>([])
  const stream = useRef<MediaStream | null>(null)
  const ticker = useRef<ReturnType<typeof setInterval> | null>(null)

  const release = () => {
    if (ticker.current) clearInterval(ticker.current)
    ticker.current = null
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null
  }

  // Leaving the page mid-recording must not leave the microphone open.
  useEffect(() => release, [])

  const start = async () => {
    setError(null)
    const mimeType = pickType()
    // TypeScript's lib types say navigator.mediaDevices is always there, so
    // an optional chain reads as unnecessary. It is not: the whole API is
    // undefined on a page served over plain http, and on some older mobile
    // browsers. Checked through a typeof so the guard survives the types
    // being more confident than the runtime.
    const devices = (
      navigator as Navigator & { mediaDevices?: MediaDevices | undefined }
    ).mediaDevices as MediaDevices | undefined
    const canRecord = typeof devices?.getUserMedia === 'function'
    if (!mimeType || !canRecord) {
      setError('This browser cannot record audio. Attach a file instead.')
      return
    }
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.current = media
      chunks.current = []

      const rec = new MediaRecorder(media, { mimeType })
      rec.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.current.push(event.data)
      }
      rec.onstop = () => {
        const blob = new Blob(chunks.current, { type: mimeType })
        release()
        setRecording(false)
        if (blob.size > 0) {
          const extension = mimeType.includes('mp4') ? 'm4a' : 'webm'
          onRecorded(
            new File([blob], `voice-note.${extension}`, { type: blob.type }),
            secondsRef.current,
          )
        }
        setSeconds(0)
      }
      recorder.current = rec
      rec.start()
      setRecording(true)
      setSeconds(0)
      ticker.current = setInterval(() => {
        setSeconds((n) => {
          const next = n + 1
          // Stops itself rather than recording into the void and failing on
          // upload, which would lose the whole thing.
          if (next >= MAX_SECONDS) rec.stop()
          return next
        })
      }, 1000)
    } catch {
      release()
      setError(
        'We could not use your microphone. Check the permission and try again.',
      )
    }
  }

  // onstop runs outside React's render, so it cannot read the state variable.
  const secondsRef = useRef(0)
  useEffect(() => {
    secondsRef.current = seconds
  }, [seconds])

  const stop = () => recorder.current?.stop()

  const cancel = () => {
    const rec = recorder.current
    if (!rec) return
    rec.onstop = () => {
      release()
      setRecording(false)
      setSeconds(0)
    }
    rec.stop()
  }

  if (error) {
    return (
      <p className="text-muted-foreground text-xs" role="status">
        {error}
      </p>
    )
  }

  if (!recording) {
    return (
      <Button
        type="button"
        variant="ghost"
        size="sm"
        disabled={disabled}
        onClick={() => void start()}
        title="Record a voice note"
      >
        <MicIcon className="size-4" />
        <span className="sr-only">Record a voice note</span>
      </Button>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <span
        className="size-2 animate-pulse rounded-full bg-red-500"
        aria-hidden
      />
      <span className="text-xs tabular-nums" role="timer">
        {readableLength(seconds)}
      </span>
      <Button type="button" variant="ghost" size="sm" onClick={stop}>
        <SquareIcon className="size-3.5" />
        <span className="ml-1.5">Stop</span>
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={cancel}>
        <Trash2Icon className="size-3.5" />
        <span className="sr-only">Discard</span>
      </Button>
    </div>
  )
}
