import { useCallback, useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import { Sidebar } from './components/Sidebar'
import { ChatHeader } from './components/ChatHeader'
import { MessageList } from './components/MessageList'
import { Composer } from './components/Composer'
import { ErrorBanner } from './components/ErrorBanner'
import { WelcomeScreen } from './components/EmptyStates'
import { useConversations } from './hooks/useConversations'
import { useThread } from './hooks/useThread'
import { useHealth } from './hooks/useHealth'
import { useMediaQuery } from './hooks/useMediaQuery'
import { useTheme } from './hooks/useTheme'

export default function App() {
  const [search, setSearch] = useState('')
  const [activeId, setActiveId] = useState(null)
  const [creating, setCreating] = useState(false)
  const [actionError, setActionError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [sidebarVisible, setSidebarVisible] = useState(true)

  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const { theme, toggle: toggleTheme } = useTheme()
  const { health, reachable } = useHealth()

  const { conversations, loading, error, create, rename, remove, touch } = useConversations(search)

  const handleReply = useCallback(
    ({ title }) => touch(activeId, { title }),
    [touch, activeId],
  )
  const thread = useThread(activeId, { onReply: handleReply })

  // On first load, open the most recently updated conversation.
  const pickedInitial = useRef(false)
  useEffect(() => {
    if (pickedInitial.current || loading || search) return
    if (conversations.length > 0) setActiveId(conversations[0].id)
    pickedInitial.current = true
  }, [conversations, loading, search])

  // If the open conversation is deleted, fall back to the next one.
  useEffect(() => {
    if (!activeId) return
    if (!loading && !search && conversations.length && !conversations.some((c) => c.id === activeId)) {
      setActiveId(conversations[0].id)
    }
  }, [conversations, activeId, loading, search])

  const handleNewChat = async () => {
    if (creating) return
    setCreating(true)
    setActionError(null)
    try {
      const conversation = await create()
      setActiveId(conversation.id)
      setSearch('')
      setDrawerOpen(false)
    } catch (err) {
      setActionError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const handleSelect = (id) => {
    setActiveId(id)
    setDrawerOpen(false)
  }

  const handleRename = async (id, title) => {
    try {
      await rename(id, title)
    } catch (err) {
      setActionError(err.message)
    }
  }

  const handleDelete = async (id) => {
    try {
      await remove(id)
      if (id === activeId) setActiveId(null)
    } catch (err) {
      setActionError(err.message)
    }
  }

  const handleSend = async (text) => {
    const result = await thread.send(text)
    if (result.ok) touch(activeId)
    return result
  }

  const [prefill, setPrefill] = useState(null)
  useEffect(() => {
    if (prefill) {
      handleSend(prefill)
      setPrefill(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill])

  const sidebar = (
    <Sidebar
      conversations={conversations}
      loading={loading}
      error={error}
      search={search}
      onSearchChange={setSearch}
      activeId={activeId}
      onSelect={handleSelect}
      onNewChat={handleNewChat}
      onRename={handleRename}
      onDelete={handleDelete}
      creating={creating}
      health={health}
      onClose={isDesktop ? undefined : () => setDrawerOpen(false)}
    />
  )

  const configWarning = !reachable
    ? 'Cannot reach the backend. Start it with: uvicorn main:app --reload --port 8000'
    : health && !health.llm_configured
      ? 'GROQ_API_KEY is not set on the server. Add it to your .env file and restart the backend.'
      : null

  return (
    <div className="flex h-full overflow-hidden bg-canvas">
      {/* Desktop: a column. Tablet/mobile: an overlay drawer. */}
      <aside
        className={clsx(
          'hidden shrink-0 border-r border-hairline lg:block',
          sidebarVisible ? 'lg:w-[280px]' : 'lg:w-0 lg:border-r-0 lg:overflow-hidden',
        )}
      >
        {sidebarVisible && sidebar}
      </aside>

      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/50"
            onClick={() => setDrawerOpen(false)}
            aria-label="Close menu"
          />
          <div className="absolute left-0 top-0 h-full w-[84%] max-w-[300px] border-r border-hairline shadow-xl">
            {sidebar}
          </div>
        </div>
      )}

      <main className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          conversation={thread.conversation}
          onOpenSidebar={() => setDrawerOpen(true)}
          sidebarOpen={sidebarVisible}
          onToggleSidebar={() => setSidebarVisible((value) => !value)}
          theme={theme}
          onToggleTheme={toggleTheme}
        />

        {(configWarning || actionError || thread.error) && (
          <div className="px-4 pt-3 sm:px-6">
            <ErrorBanner
              message={configWarning ?? actionError ?? thread.error}
              tone={configWarning ? 'warning' : 'danger'}
              onDismiss={
                configWarning
                  ? undefined
                  : () => {
                      setActionError(null)
                      thread.clearError()
                    }
              }
            />
          </div>
        )}

        {activeId ? (
          <>
            <MessageList
              messages={thread.messages}
              sourcesByMessage={thread.sourcesByMessage}
              loading={thread.loading}
              sending={thread.sending}
              onPickPrompt={setPrefill}
            />
            <Composer
              onSend={handleSend}
              sending={thread.sending}
              disabled={thread.loading || !reachable}
              placeholder={thread.sending ? 'Waiting for the reply…' : 'Send a message'}
            />
          </>
        ) : (
          <WelcomeScreen onNewChat={handleNewChat} creating={creating} />
        )}
      </main>
    </div>
  )
}
