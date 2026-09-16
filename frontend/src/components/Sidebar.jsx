import { Database, Plus, Search, X } from 'lucide-react'
import { ConversationItem } from './ConversationItem'
import { groupByRecency } from '../lib/format'

function SidebarSkeleton() {
  return (
    <div className="space-y-2 px-2" aria-hidden="true">
      {[...Array(5)].map((_, index) => (
        <div key={index} className="h-11 rounded-lg bg-raised/70" />
      ))}
    </div>
  )
}

export function Sidebar({
  conversations,
  loading,
  error,
  search,
  onSearchChange,
  activeId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
  creating,
  health,
  onClose,
}) {
  const groups = groupByRecency(conversations)

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center gap-2 px-3 py-3">
        <button
          type="button"
          onClick={onNewChat}
          disabled={creating}
          className="btn-outline flex-1 justify-start"
        >
          <Plus size={16} strokeWidth={2.2} />
          <span>{creating ? 'Creating…' : 'New chat'}</span>
        </button>
        {onClose && (
          <button type="button" onClick={onClose} className="btn-ghost lg:hidden" aria-label="Close menu">
            <X size={18} />
          </button>
        )}
      </div>

      <div className="px-3 pb-3">
        <div className="relative">
          <Search
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
          />
          <input
            type="search"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search chats and messages"
            aria-label="Search conversations"
            className="w-full rounded-lg border border-hairline bg-canvas py-2 pl-9 pr-3 text-sm
                       text-ink placeholder:text-faint focus:border-accent focus:outline-none"
          />
        </div>
      </div>

      <nav className="scroll-area flex-1 overflow-y-auto pb-4" aria-label="Conversations">
        {loading ? (
          <SidebarSkeleton />
        ) : error ? (
          <p className="px-4 text-[13px] leading-relaxed text-danger">{error}</p>
        ) : conversations.length === 0 ? (
          <p className="px-4 text-[13px] leading-relaxed text-muted">
            {search
              ? `Nothing matches “${search}”.`
              : 'No chats yet. Start one to see it listed here.'}
          </p>
        ) : (
          groups.map((group) => (
            <section key={group.label} className="mb-4">
              <h2 className="px-4 pb-1.5 text-[11px] font-medium tracking-wide text-faint">
                {group.label}
              </h2>
              <ul className="space-y-0.5 px-2">
                {group.items.map((conversation) => (
                  <li key={conversation.id}>
                    <ConversationItem
                      conversation={conversation}
                      active={conversation.id === activeId}
                      onSelect={onSelect}
                      onRename={onRename}
                      onDelete={onDelete}
                    />
                  </li>
                ))}
              </ul>
            </section>
          ))
        )}
      </nav>

      <footer className="border-t border-hairline px-4 py-3">
        <div className="flex items-center gap-2 text-[11px] text-muted">
          <Database size={13} className={health?.rag_available ? 'text-grounded' : 'text-faint'} />
          <span>
            {health?.rag_available
              ? `Knowledge base: ${health.rag_documents} passages`
              : 'Knowledge base off'}
          </span>
        </div>
        <p className="mt-1 truncate font-mono text-[11px] text-faint">
          {health?.llm_model ?? 'model unavailable'}
        </p>
      </footer>
    </div>
  )
}
