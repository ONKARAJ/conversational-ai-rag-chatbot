import { memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import SyntaxHighlighter from 'react-syntax-highlighter/dist/esm/prism-light'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash'
import css from 'react-syntax-highlighter/dist/esm/languages/prism/css'
import javascript from 'react-syntax-highlighter/dist/esm/languages/prism/javascript'
import json from 'react-syntax-highlighter/dist/esm/languages/prism/json'
import jsx from 'react-syntax-highlighter/dist/esm/languages/prism/jsx'
import markup from 'react-syntax-highlighter/dist/esm/languages/prism/markup'
import python from 'react-syntax-highlighter/dist/esm/languages/prism/python'
import sql from 'react-syntax-highlighter/dist/esm/languages/prism/sql'
import typescript from 'react-syntax-highlighter/dist/esm/languages/prism/typescript'
import yaml from 'react-syntax-highlighter/dist/esm/languages/prism/yaml'
import { CopyButton } from './CopyButton'

// Registering a short list instead of importing every Prism grammar keeps the
// bundle small; anything unregistered still renders as plain monospace text.
Object.entries({ bash, css, javascript, json, jsx, markup, python, sql, typescript, yaml }).forEach(
  ([name, definition]) => SyntaxHighlighter.registerLanguage(name, definition),
)

function CodeBlock({ language, code }) {
  return (
    <figure className="my-4 overflow-hidden rounded-lg border border-hairline bg-[#282c34]">
      <figcaption className="flex items-center justify-between border-b border-black/30 bg-black/20 px-3 py-1.5">
        <span className="font-mono text-xs text-white/60">{language || 'code'}</span>
        <CopyButton
          value={code}
          label="Copy code"
          className="!text-white/60 hover:!bg-white/10 hover:!text-white"
        />
      </figcaption>
      <SyntaxHighlighter
        language={language || 'text'}
        style={oneDark}
        customStyle={{
          margin: 0,
          background: 'transparent',
          padding: '1rem',
          fontSize: '13px',
          lineHeight: 1.6,
        }}
        codeTagProps={{ style: { fontFamily: '"JetBrains Mono", ui-monospace, monospace' } }}
        wrapLongLines={false}
      >
        {code}
      </SyntaxHighlighter>
    </figure>
  )
}

/** Renders assistant Markdown: GFM tables, lists, links and fenced code. */
export const MarkdownMessage = memo(function MarkdownMessage({ content }) {
  return (
    <div className="prose-chat">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ inline, className, children, ...props }) {
            const text = String(children).replace(/\n$/, '')
            const match = /language-(\w+)/.exec(className || '')
            if (inline || (!match && !text.includes('\n'))) {
              return (
                <code className={className} {...props}>
                  {children}
                </code>
              )
            }
            return <CodeBlock language={match?.[1]} code={text} />
          },
          // Code blocks render their own <figure>, so <pre> just passes through.
          pre({ children }) {
            return <>{children}</>
          },
          a({ children, ...props }) {
            return (
              <a {...props} target="_blank" rel="noreferrer noopener">
                {children}
              </a>
            )
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto">
                <table>{children}</table>
              </div>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
})
