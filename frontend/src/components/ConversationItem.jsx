import { useEffect, useRef, useState } from 'react'
import { Check, MoreHorizontal, Pencil, Trash2, X } from 'lucide-react'
import clsx from 'clsx'
import { relativeTime } from '../lib/format'

export function ConversationItem({ conversation, active, onSelect, onRename, onDelete }) {
  const [mode, setMode] = useState('idle') // idle | menu | renaming | confirming
  const [draft, setDraft] = useState(conversation.title)
  const inputRef = useRef(null)

  useEffect(() => {
    if (mode === 'renaming') {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [mode])

  useEffect(() => {
    setDraft(conversation.title)
  }, [conversation.title])

  const commitRename = async () => {
    const title = draft.trim()
    setMode('idle')
    if (title && title !== conversation.title) await onRename(conversation.id, title)
    else setDraft(conversation.title)
  }

  if (mode === 'renaming') {
    return (
      <div className="flex items-center gap-1 rounded-lg border border-accent bg-surface px-2 py-1.5">
        <input
          ref={inputRef}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') commitRename()
            if (event.key === 'Escape') {
              setDraft(conversation.title)
              setMode('idle')
            }
          }}
          className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none"
          aria-label="Conversation name"
          maxLength={120}
        />
        <button type="button" onClick={commitRename} className="btn-ghost !px-1.5" aria-label="Save name">
          <Check size={14} />
        </button>
        <button
          type="button"
          onClick={() => {
            setDraft(conversation.title)
            setMode('idle')
          }}
          className="btn-ghost !px-1.5"
          aria-label="Cancel rename"
        >
          <X size={14} />
        </button>
      </div>
    )
  }

  if (mode === 'confirming') {
    return (
      <div className="rounded-lg border border-danger bg-danger-soft px-3 py-2">
        <p className="text-[13px] leading-snug text-ink">Delete this chat and its messages?</p>
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={() => onDelete(conversation.id)}
            className="btn rounded-md bg-danger px-2.5 py-1 text-xs text-white hover:brightness-110"
          >
            Delete
          </button>
          <button
            type="button"
            onClick={() => setMode('idle')}
            className="btn rounded-md px-2.5 py-1 text-xs text-muted hover:text-ink"
          >
            Keep
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className={clsx(
        'group relative flex items-center gap-1 rounded-lg transition-colors',
        active ? 'bg-raised' : 'hover:bg-raised/70',
      )}
    >
      <button
        type="button"
        onClick={() => onSelect(conversation.id)}
        className="min-w-0 flex-1 px-3 py-2 text-left"
        aria-current={active ? 'true' : undefined}
      >
        <span
          className={clsx(
            'block truncate text-sm',
            active ? 'font-medium text-ink' : 'text-muted group-hover:text-ink',
          )}
        >
          {conversation.title}
        </span>
        <span className="mt-0.5 block font-mono text-[11px] text-faint">
          {relativeTime(conversation.updated_at)}
          {conversation.message_count > 0 && ` · ${conversation.message_count} msgs`}
        </span>
      </button>

      <div className="flex items-center pr-1.5">
        {mode === 'menu' ? (
          <div className="flex items-center gap-0.5">
            <button
              type="button"
              onClick={() => setMode('renaming')}
              className="btn-ghost !px-1.5"
              aria-label={`Rename ${conversation.title}`}
            >
              <Pencil size={14} />
            </button>
            <button
              type="button"
              onClick={() => setMode('confirming')}
              className="btn-ghost !px-1.5 hover:!text-danger"
              aria-label={`Delete ${conversation.title}`}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setMode('menu')}
            onBlur={() => setTimeout(() => setMode((m) => (m === 'menu' ? 'idle' : m)), 200)}
            className={clsx(
              'btn-ghost !px-1.5 opacity-0 focus-visible:opacity-100 group-hover:opacity-100',
              active && 'opacity-60',
            )}
            aria-label={`Actions for ${conversation.title}`}
          >
            <MoreHorizontal size={15} />
          </button>
        )}
      </div>
    </div>
  )
}
