import clsx from 'clsx'
import { Sparkles } from 'lucide-react'
import { MarkdownMessage } from './MarkdownMessage'
import { SourcesStrip } from './SourcesStrip'
import { CopyButton } from './CopyButton'
import { clockTime } from '../lib/format'

/**
 * Two deliberately different shapes:
 *  - the user's turn is a compact right-aligned card (a quoted input),
 *  - the assistant's turn is full-width prose with its own action row,
 * so the eye can tell them apart without reading a label.
 */
export function Message({ message, sources }) {
  const isUser = message.role === 'human'

  if (isUser) {
    return (
      <article className="flex justify-end animate-fade-in">
        <div
          className={clsx(
            'max-w-[85%] rounded-2xl rounded-br-md border border-hairline bg-raised px-4 py-2.5',
            message.pending && 'opacity-60',
          )}
        >
          <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed text-ink">
            {message.content}
          </p>
        </div>
      </article>
    )
  }

  return (
    <article className="group animate-fade-in">
      <div className="mb-1.5 flex items-center gap-2">
        <span
          className="grid h-6 w-6 place-items-center rounded-md bg-accent-soft text-accent"
          aria-hidden="true"
        >
          <Sparkles size={13} strokeWidth={2.2} />
        </span>
        <span className="text-xs font-medium text-muted">Assistant</span>
        <span className="font-mono text-[11px] text-faint">{clockTime(message.created_at)}</span>
      </div>

      <div className="pl-8">
        <MarkdownMessage content={message.content} />
        <SourcesStrip sources={sources} />

        <div className="mt-2 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
          <CopyButton value={message.content} label="Copy response" className="-ml-2.5" />
        </div>
      </div>
    </article>
  )
}
