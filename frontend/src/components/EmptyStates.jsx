import { MessageSquarePlus } from 'lucide-react'

const STARTERS = [
  "How does RunnableWithMessageHistory keep this session's context isolated from my other chats?",
  "What's in your knowledge base right now, and how does retrieval scoring work?",
  "Explain the trade-off between chunk size and retrieval accuracy in a RAG pipeline.",
  "Walk me through what happens between me hitting send and getting a response — memory, retrieval, generation.",
]

/** Shown inside an open conversation that has no messages yet. */
export function ThreadEmptyState({ onPickPrompt }) {
  return (
    <div className="py-12">
      <h2 className="text-2xl font-semibold tracking-tight">Start the conversation</h2>
      <p className="mt-2 max-w-md text-[15px] leading-relaxed text-muted">
        This chat has its own memory. Anything you say here stays here — other conversations
        cannot see it.
      </p>

      <ul className="mt-6 grid gap-2 sm:grid-cols-2">
        {STARTERS.map((prompt) => (
          <li key={prompt}>
            <button
              type="button"
              onClick={() => onPickPrompt?.(prompt)}
              className="w-full rounded-xl border border-hairline bg-surface px-4 py-3 text-left
                         text-[14px] leading-snug text-muted transition-colors
                         hover:border-accent hover:text-ink"
            >
              {prompt}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Shown when the database has no conversations at all. */
export function WelcomeScreen({ onNewChat, creating }) {
  return (
    <div className="flex flex-1 items-center justify-center px-6">
      <div className="max-w-md text-center">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-accent-soft text-accent">
          <MessageSquarePlus size={22} strokeWidth={2} />
        </span>
        <h1 className="mt-5 text-2xl font-semibold tracking-tight">No conversations yet</h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted">
          Each chat you start gets its own session id and its own memory, stored on the backend.
          Create one to begin.
        </p>
        <button type="button" onClick={onNewChat} disabled={creating} className="btn-primary mt-6">
          {creating ? 'Creating…' : 'Start a conversation'}
        </button>
      </div>
    </div>
  )
}
