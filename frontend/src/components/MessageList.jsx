import { useEffect, useRef } from 'react'
import { Message } from './Message'
import { ThreadEmptyState } from './EmptyStates'

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 pl-8 text-muted" role="status" aria-live="polite">
      <span className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((index) => (
          <span
            key={index}
            className="h-1.5 w-1.5 rounded-full bg-accent animate-blink"
            style={{ animationDelay: `${index * 160}ms` }}
          />
        ))}
      </span>
      <span className="text-xs">Thinking…</span>
    </div>
  )
}

function SkeletonThread() {
  return (
    <div className="space-y-6" aria-hidden="true">
      {[70, 45, 85].map((width, index) => (
        <div key={index} className="space-y-2">
          <div className="h-3 w-20 rounded bg-raised" />
          <div className="h-3 rounded bg-raised" style={{ width: `${width}%` }} />
          <div className="h-3 w-1/2 rounded bg-raised" />
        </div>
      ))}
    </div>
  )
}

export function MessageList({ messages, sourcesByMessage, loading, sending, onPickPrompt }) {
  const bottomRef = useRef(null)
  const containerRef = useRef(null)

  // Auto-scroll to the newest message, but leave the user alone if they have
  // scrolled up to read something earlier.
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight
    if (distanceFromBottom < 240 || sending) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [messages, sending])

  return (
    <div ref={containerRef} className="scroll-area flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-thread px-4 py-6 sm:px-6">
        {loading && messages.length === 0 ? (
          <SkeletonThread />
        ) : messages.length === 0 ? (
          <ThreadEmptyState onPickPrompt={onPickPrompt} />
        ) : (
          <div className="space-y-7">
            {messages.map((message) => (
              <Message
                key={message.id}
                message={message}
                sources={sourcesByMessage[message.id]}
              />
            ))}
            {sending && <TypingIndicator />}
          </div>
        )}
        <div ref={bottomRef} className="h-2" />
      </div>
    </div>
  )
}
