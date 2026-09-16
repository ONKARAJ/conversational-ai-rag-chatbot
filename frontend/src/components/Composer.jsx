import { useEffect, useRef, useState } from 'react'
import { ArrowUp } from 'lucide-react'
import clsx from 'clsx'

const MAX_HEIGHT = 200

/**
 * The composer owns the draft text. Enter sends, Shift+Enter adds a newline,
 * the button and the key handler share one guarded submit path, and the field
 * is only cleared once the request has actually been accepted — if the send
 * fails, the parent hands the text back so nothing typed is lost.
 */
export function Composer({ onSend, disabled, sending, placeholder }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)
  const submittingRef = useRef(false)

  // Grow with the content, up to a cap, then scroll inside the field.
  useEffect(() => {
    const element = textareaRef.current
    if (!element) return
    element.style.height = 'auto'
    element.style.height = `${Math.min(element.scrollHeight, MAX_HEIGHT)}px`
  }, [value])

  useEffect(() => {
    if (!disabled && !sending) textareaRef.current?.focus()
  }, [disabled, sending])

  const submit = async () => {
    const text = value.trim()
    if (!text || disabled || sending || submittingRef.current) return

    submittingRef.current = true
    setValue('') // clear immediately so the user sees the send happen
    const result = await onSend(text)
    if (result?.restore) setValue(result.restore) // failed — give the text back
    submittingRef.current = false
    textareaRef.current?.focus()
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  const canSend = value.trim().length > 0 && !disabled && !sending

  return (
    <div className="border-t border-hairline bg-canvas px-4 pb-4 pt-3 sm:px-6">
      <div className="mx-auto w-full max-w-thread">
        <div
          className={clsx(
            'flex items-end gap-2 rounded-2xl border bg-surface px-3 py-2 transition-colors',
            disabled ? 'border-hairline opacity-60' : 'border-hairline focus-within:border-accent',
          )}
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            disabled={disabled}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder ?? 'Send a message'}
            aria-label="Message"
            className="scroll-area max-h-[200px] flex-1 resize-none bg-transparent py-1.5 text-[15px]
                       leading-relaxed text-ink placeholder:text-faint focus:outline-none
                       disabled:cursor-not-allowed"
          />
          <button
            type="button"
            onClick={submit}
            disabled={!canSend}
            className={clsx(
              'btn mb-0.5 h-8 w-8 shrink-0 rounded-lg',
              canSend
                ? 'bg-accent text-[color:var(--accent-ink)] hover:bg-accent-hover'
                : 'bg-raised text-faint',
            )}
            aria-label={sending ? 'Waiting for the reply' : 'Send message'}
          >
            <ArrowUp size={16} strokeWidth={2.4} />
          </button>
        </div>

        <p className="mt-2 text-center text-[11px] text-faint">
          Enter sends · Shift + Enter adds a line · replies can be wrong, check anything important
        </p>
      </div>
    </div>
  )
}
