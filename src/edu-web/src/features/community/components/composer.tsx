/**
 * Writing something in the class room.
 *
 * Four things can come out of this box: a message, a message with files, a
 * voice note, or a poll. They share one composer rather than four buttons at
 * the top, because a student thinking of a question should not first have to
 * decide what kind of question it is.
 *
 * The server refuses contact details and says exactly which kind it found.
 * That wording is shown as it arrives: "this looks like it contains a phone
 * number" tells a student what to change, and a generic failure leaves them
 * retyping the same post until they give up.
 *
 * Which is why the failure is read off the atom rather than caught. The
 * setter from useAtomSet does not reject - a failing effect lands in the
 * atom's own Result - so a try/catch around it never runs. Tested on the
 * live site: the server refused a phone number with a 400, the post
 * correctly did not appear, and the student was told nothing at all.
 */

import { useEffect, useRef, useState } from 'react'
import { useAtom } from '@effect-atom/atom-react'
import { Cause } from 'effect'
import {
  BarChart3Icon,
  PaperclipIcon,
  PlusIcon,
  SendIcon,
  XIcon,
} from 'lucide-react'
import { readableSize } from './attachment-view'
import { VoiceRecorder } from './voice-recorder'
import { addPostAtom, addPostWithFilesAtom } from '@/data-acess/community'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

const MAX_BODY = 2000
const MAX_FILES = 5
const MAX_BYTES = 50 * 1024 * 1024
const MAX_POLL_OPTIONS = 6

/** What the file picker offers, matching what the server will accept. */
const ACCEPT = [
  'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/heic',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/plain', 'text/csv',
].join(',')

type Picked = { file: File; duration: number | null }

export const Composer = ({
  parentId,
  placeholder,
  onDone,
  autoFocus,
}: {
  parentId?: string
  placeholder: string
  onDone?: () => void
  autoFocus?: boolean
}) => {
  const [postResult, addPost] = useAtom(addPostAtom)
  const [filesResult, addWithFiles] = useAtom(addPostWithFilesAtom)

  const [body, setBody] = useState('')
  const [files, setFiles] = useState<Array<Picked>>([])
  const [polling, setPolling] = useState(false)
  const [question, setQuestion] = useState('')
  const [options, setOptions] = useState(['', ''])
  const [busy, setBusy] = useState(false)
  // Which atom the outcome should be read from, or null when idle.
  const [sent, setSent] = useState<'text' | 'files' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const picker = useRef<HTMLInputElement>(null)

  const left = MAX_BODY - body.length
  const filled = options.filter((o) => o.trim()).length
  const canSend =
    !busy &&
    (polling
      ? question.trim().length > 0 && filled >= 2
      : body.trim().length > 0 || files.length > 0) &&
    left >= 0

  const reset = () => {
    setBody('')
    setFiles([])
    setPolling(false)
    setQuestion('')
    setOptions(['', ''])
    setError(null)
  }

  const pick = (chosen: FileList | null) => {
    if (!chosen) return
    setError(null)
    const room = MAX_FILES - files.length
    const taken: Array<Picked> = []
    for (const file of Array.from(chosen).slice(0, room)) {
      // Checked here as well as on the server. Finding out a 60MB file is
      // too big after uploading it on a slow connection is the worst
      // possible moment to be told.
      if (file.size > MAX_BYTES) {
        setError(`${file.name} is larger than 50MB.`)
        continue
      }
      if (file.size === 0) {
        setError(`${file.name} is empty.`)
        continue
      }
      taken.push({ file, duration: null })
    }
    if (Array.from(chosen).length > room) {
      setError(`You can attach ${MAX_FILES} files to one post.`)
    }
    setFiles((was) => [...was, ...taken])
    if (picker.current) picker.current.value = ''
  }

  const send = async () => {
    setBusy(true)
    setError(null)
    const sending = files.length > 0 ? 'files' : 'text'
    try {
      if (sending === 'files') {
        await addWithFiles({
          body,
          parentId,
          files: files.map((f) => f.file),
          durations: files.map((f) => f.duration),
        })
      } else {
        await addPost({
          body,
          parentId,
          pollQuestion: polling ? question : undefined,
          pollOptions: polling ? options : undefined,
        })
      }
    } finally {
      setBusy(false)
      setSent(sending)
    }
  }

  /**
   * Clear the box once the post has actually landed, and show the server's
   * refusal when it has not.
   *
   * Both have to happen here rather than in send(), because the setter does
   * not reject and does not report success either: the outcome arrives as a
   * new Result on the next render. Clearing optimistically in send() would
   * throw away a post the server had just rejected, which is the one moment
   * the text is hardest to get back.
   */
  const result = sent === 'files' ? filesResult : postResult
  useEffect(() => {
    if (sent === null || result.waiting) return
    if (result._tag === 'Failure') {
      const thrown = Cause.squash(result.cause)
      setError(
        thrown instanceof Error && thrown.message
          ? thrown.message
          : 'That did not go through. Try again in a moment.',
      )
      setSent(null)
      return
    }
    if (result._tag === 'Success') {
      reset()
      setSent(null)
      onDone?.()
    }
    // onDone and reset are intentionally not dependencies: they change
    // identity on every render of the parent, which would re-run this on
    // every keystroke.
  }, [sent, result._tag, result.waiting])

  return (
    <div className="space-y-2">
      <Textarea
        value={body}
        autoFocus={autoFocus}
        onChange={(e) => setBody(e.target.value)}
        placeholder={polling ? 'Say something about the poll (optional)…' : placeholder}
        className="min-h-20 resize-none"
        maxLength={MAX_BODY + 200}
        onKeyDown={(e) => {
          // Enter alone makes a new line. A student writing out a derivation
          // needs line breaks far more than they need one fewer click.
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && canSend) {
            e.preventDefault()
            void send()
          }
        }}
      />

      {polling ? (
        <div className="space-y-2 rounded-lg border p-3">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What are you asking the class?"
            maxLength={300}
          />
          {options.map((option, index) => (
            <div key={index} className="flex gap-2">
              <Input
                value={option}
                onChange={(e) =>
                  setOptions((was) =>
                    was.map((o, i) => (i === index ? e.target.value : o)),
                  )
                }
                placeholder={`Option ${index + 1}`}
                maxLength={120}
              />
              {options.length > 2 ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    setOptions((was) => was.filter((_, i) => i !== index))
                  }
                  aria-label={`Remove option ${index + 1}`}
                >
                  <XIcon className="size-4" />
                </Button>
              ) : null}
            </div>
          ))}
          {options.length < MAX_POLL_OPTIONS ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setOptions((was) => [...was, ''])}
            >
              <PlusIcon className="size-3.5" />
              <span className="ml-1.5">Add option</span>
            </Button>
          ) : null}
        </div>
      ) : null}

      {files.length > 0 ? (
        <ul className="space-y-1.5">
          {files.map((picked, index) => (
            <li
              key={`${picked.file.name}-${index}`}
              className="bg-muted/40 flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
            >
              <span className="min-w-0 flex-1 truncate">{picked.file.name}</span>
              <span className="text-muted-foreground shrink-0 text-xs">
                {readableSize(picked.file.size)}
              </span>
              <button
                type="button"
                onClick={() =>
                  setFiles((was) => was.filter((_, i) => i !== index))
                }
                aria-label={`Remove ${picked.file.name}`}
                className="text-muted-foreground hover:text-foreground shrink-0"
              >
                <XIcon className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {error ? (
        <p className="text-destructive text-sm" role="alert">
          {error}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-1">
        <input
          ref={picker}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => pick(e.target.files)}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={busy || files.length >= MAX_FILES}
          onClick={() => picker.current?.click()}
          title="Attach photos or files"
        >
          <PaperclipIcon className="size-4" />
          <span className="sr-only">Attach a file</span>
        </Button>

        <VoiceRecorder
          disabled={busy || files.length >= MAX_FILES}
          onRecorded={(file, seconds) =>
            setFiles((was) => [...was, { file, duration: seconds }])
          }
        />

        {!parentId ? (
          <Button
            type="button"
            variant={polling ? 'secondary' : 'ghost'}
            size="sm"
            disabled={busy}
            onClick={() => setPolling((was) => !was)}
            title="Ask the class to vote"
          >
            <BarChart3Icon className="size-4" />
            <span className="sr-only">Make a poll</span>
          </Button>
        ) : null}

        <span className="flex-1" />

        {left < 200 ? (
          <span
            className={
              left < 0
                ? 'text-destructive text-xs tabular-nums'
                : 'text-muted-foreground text-xs tabular-nums'
            }
          >
            {left}
          </span>
        ) : null}

        {onDone ? (
          <Button type="button" variant="ghost" size="sm" onClick={onDone}>
            Cancel
          </Button>
        ) : null}

        <Button type="button" size="sm" disabled={!canSend} onClick={() => void send()}>
          <SendIcon className="size-3.5" />
          <span className="ml-1.5">{parentId ? 'Reply' : 'Post'}</span>
        </Button>
      </div>
    </div>
  )
}
