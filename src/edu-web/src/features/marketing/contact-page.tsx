import { BuildingIcon, MailIcon, UserRoundIcon } from 'lucide-react'
import { useState } from 'react'
import { Reveal, SectionHeading } from './bits'
import { MarketingLayout } from './marketing-layout'
import { college, contactEmail, supervisor } from './site-data'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

const reasons = [
  'I am a student and something is not working',
  'I teach FSc and want to try this with a class',
  'I am judging or reviewing the project',
  'Something else',
] as const

export const ContactPage = () => {
  const [name, setName] = useState('')
  const [reason, setReason] = useState<string>(reasons[0])
  const [message, setMessage] = useState('')

  // No form endpoint to post to, so the form composes a mail instead of
  // pretending to send one.
  const send = () => {
    const subject = `NISAAB — ${reason}`
    const body = `${message}\n\n— ${name || 'A visitor'}`
    window.location.href = `mailto:${contactEmail}?subject=${encodeURIComponent(
      subject,
    )}&body=${encodeURIComponent(body)}`
  }

  return (
    <MarketingLayout>
      <section className="mx-auto w-full max-w-6xl px-4 pt-20 pb-16 sm:px-6">
        <Reveal>
          <SectionHeading
            eyebrow="Contact"
            title="Tell us what is missing."
            blurb="We are students building this alongside our own FSc year, so the fastest way to improve it is to hear where it falls short."
          />
        </Reveal>
      </section>

      <section className="border-t">
        <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.2fr_1fr]">
          <Reveal>
            <div className="bg-card rounded-2xl border p-6 sm:p-8">
              <div className="grid gap-5">
                <div className="grid gap-2">
                  <Label htmlFor="contact-name">Your name</Label>
                  <Input
                    id="contact-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Optional"
                  />
                </div>

                <div className="grid gap-2">
                  <Label>What is this about?</Label>
                  <div className="grid gap-2">
                    {reasons.map((option) => (
                      <button
                        key={option}
                        type="button"
                        onClick={() => setReason(option)}
                        className={
                          'rounded-lg border p-3 text-left text-sm transition-colors ' +
                          (reason === option
                            ? 'border-primary bg-primary/5 ring-primary ring-1'
                            : 'hover:border-primary/50 hover:bg-accent/50')
                        }
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="contact-message">Message</Label>
                  <Textarea
                    id="contact-message"
                    rows={5}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="What happened, or what would help?"
                  />
                </div>

                <Button onClick={send} disabled={!message.trim()} className="w-full">
                  <MailIcon className="size-4" />
                  Open in your mail app
                </Button>
                <p className="text-muted-foreground text-xs">
                  This opens your own mail app with the message ready — nothing is sent
                  from this page.
                </p>
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.12}>
            <div className="space-y-4">
              {[
                { icon: MailIcon, label: 'Email', value: contactEmail },
                { icon: BuildingIcon, label: 'College', value: college },
                { icon: UserRoundIcon, label: 'Supervisor', value: supervisor },
              ].map((item) => (
                <div key={item.label} className="bg-card rounded-2xl border p-5">
                  <div className="text-muted-foreground flex items-center gap-2 text-sm font-medium">
                    <item.icon className="size-4" />
                    {item.label}
                  </div>
                  <div className="mt-1.5 text-pretty">{item.value}</div>
                </div>
              ))}

              <div className="bg-muted/50 rounded-2xl border p-5">
                <div className="font-semibold">For teachers and judges</div>
                <p className="text-muted-foreground mt-1.5 text-sm text-pretty">
                  Happy to walk through how the syllabus is modelled, how questions are
                  generated and marked, or to set up accounts for a class. Say so in the
                  message and we will arrange it.
                </p>
              </div>
            </div>
          </Reveal>
        </div>
      </section>
    </MarketingLayout>
  )
}
