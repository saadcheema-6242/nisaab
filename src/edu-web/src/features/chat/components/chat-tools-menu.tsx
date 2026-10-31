import { GlobeIcon, SlidersHorizontalIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

/**
 * What the student may tick beside the message box.
 *
 * The value is the tool's real name, because the server checks the choice
 * against the tool it is about to run - the label is only what the student
 * reads. Ticking nothing means no restriction, which is the usual case.
 */
export const CHAT_TOOLS = [
  { name: 'practice_quiz', label: 'Quiz maker' },
  { name: 'practice_paper', label: 'Paper maker' },
  { name: 'generate_image', label: 'Image maker' },
  { name: 'practice_flashcards', label: 'Flashcards' },
  { name: 'practice_mind_map', label: 'Mind map' },
] as const

type Props = {
  tools: ReadonlyArray<string>
  onToolsChange: (tools: ReadonlyArray<string>) => void
  webSearch: boolean
  onWebSearchChange: (on: boolean) => void
}

export const ChatToolsMenu = ({
  tools,
  onToolsChange,
  webSearch,
  onWebSearchChange,
}: Props) => {
  const toggle = (name: string) =>
    onToolsChange(
      tools.includes(name)
        ? tools.filter((t) => t !== name)
        : [...tools, name],
    )

  const chosen = CHAT_TOOLS.filter((t) => tools.includes(t.name))
  const summary =
    chosen.length === 0
      ? 'Tools'
      : chosen.length === 1
        ? chosen[0].label
        : `${chosen.length} tools`

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5">
          <SlidersHorizontalIcon className="size-4" />
          <span className="text-xs">{summary}</span>
          {!webSearch && <GlobeIcon className="size-3.5 opacity-40" />}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
          Leave all unticked to let the tutor choose
        </DropdownMenuLabel>
        {CHAT_TOOLS.map((tool) => (
          <DropdownMenuCheckboxItem
            key={tool.name}
            checked={tools.includes(tool.name)}
            onCheckedChange={() => toggle(tool.name)}
            onSelect={(event) => event.preventDefault()}
          >
            {tool.label}
          </DropdownMenuCheckboxItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuCheckboxItem
          checked={webSearch}
          onCheckedChange={(on) => onWebSearchChange(Boolean(on))}
          onSelect={(event) => event.preventDefault()}
        >
          Search the web
        </DropdownMenuCheckboxItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
