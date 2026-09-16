import { Menu, Moon, PanelLeft, Sun } from 'lucide-react'
import { CopyButton } from './CopyButton'

/**
 * The session id sits in the header on purpose: this project is about
 * per-conversation memory, so the id that scopes that memory should be
 * visible, not hidden in a network tab.
 */
export function ChatHeader({ conversation, onOpenSidebar, sidebarOpen, onToggleSidebar, theme, onToggleTheme }) {
  return (
    <header className="flex items-center gap-3 border-b border-hairline bg-surface/80 px-4 py-3 backdrop-blur">
      <button type="button" onClick={onOpenSidebar} className="btn-ghost lg:hidden" aria-label="Open menu">
        <Menu size={18} />
      </button>
      <button
        type="button"
        onClick={onToggleSidebar}
        className="btn-ghost hidden lg:inline-flex"
        aria-label={sidebarOpen ? 'Hide conversation list' : 'Show conversation list'}
      >
        <PanelLeft size={17} />
      </button>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-sm font-medium text-ink">
          {conversation?.title ?? 'Conversational AI'}
        </h1>
        {conversation && (
          <div className="flex items-center gap-1">
            <span className="truncate font-mono text-[11px] text-faint">{conversation.id}</span>
            <CopyButton
              value={conversation.id}
              label="Copy session id"
              iconOnly
              className="!px-1 !py-0.5"
            />
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={onToggleTheme}
        className="btn-ghost"
        aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      >
        {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
      </button>
    </header>
  )
}
