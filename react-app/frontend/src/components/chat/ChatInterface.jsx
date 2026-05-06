import React, { useState, useRef, useEffect } from 'react'
import { Send, MessageCircle, AlertCircle, CheckCircle, Clock, PlusCircle, Sparkles } from 'lucide-react'
import { useExpansionAgent } from '../../services/expansionAgentAPI'
import { cn } from '../../lib/utils'

const QUICK_QUESTIONS = [
  "What are the top 5 expansion opportunities?",
  "Show expansion candidates in Boston Metro with low competition",
  "Show existing store performance",
]

/**
 * Parse markdown table rows into structured data
 */
function parseTableRow(line) {
  return line
    .split('|')
    .slice(1, -1) // Remove empty first/last from leading/trailing |
    .map(cell => cell.trim())
}

/**
 * Check if a line is a table separator (e.g., |---|---|)
 */
function isTableSeparator(line) {
  return /^\|[\s\-:]+\|/.test(line) && line.includes('-')
}

/**
 * Render a markdown table
 */
function MarkdownTable({ rows }) {
  if (rows.length < 2) return null

  const headerRow = parseTableRow(rows[0])
  const dataRows = rows.slice(2).map(parseTableRow) // Skip header and separator

  return (
    <div className="overflow-x-auto my-2 rounded-lg border border-gray-200/70">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50/80 border-b border-gray-200/70">
          <tr>
            {headerRow.map((cell, idx) => (
              <th key={idx} className="px-3 py-2 text-left font-semibold text-gray-700 text-xs">
                {formatInlineText(cell)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataRows.map((row, rowIdx) => (
            <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}>
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} className="px-3 py-2 text-gray-700 border-b border-gray-100/70 last:border-b-0">
                  {formatInlineText(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Simple markdown-like text renderer
 * Handles bold, headers, lists, and tables without external dependencies
 */
function SimpleMarkdown({ content }) {
  if (!content) return null

  const lines = content.split('\n')
  const elements = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Check if this is the start of a table
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const tableRows = []
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableRows.push(lines[i])
        i++
      }
      // Only render as table if we have header + separator + at least one data row
      if (tableRows.length >= 3 && isTableSeparator(tableRows[1])) {
        elements.push(<MarkdownTable key={`table-${i}`} rows={tableRows} />)
      } else {
        // Not a valid table, render as paragraphs
        tableRows.forEach((row, idx) => {
          elements.push(
            <p key={`${i}-${idx}`} className="text-sm text-gray-700 mb-2">
              {formatInlineText(row)}
            </p>
          )
        })
      }
      continue
    }

    // Headers
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="font-semibold text-gray-800 mt-2.5 mb-1 text-sm">
          {line.slice(4)}
        </h3>
      )
    } else if (line.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="font-semibold text-gray-800 mt-2.5 mb-1 text-[15px]">
          {line.slice(3)}
        </h2>
      )
    } else if (line.startsWith('# ')) {
      elements.push(
        <h1 key={i} className="font-bold text-gray-900 mt-2.5 mb-1.5 text-base">
          {line.slice(2)}
        </h1>
      )
    }
    // Bullet points
    else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(
        <li key={i} className="ml-4 text-sm text-gray-700 leading-relaxed">
          {formatInlineText(line.slice(2))}
        </li>
      )
    }
    // Numbered lists
    else if (/^\d+\.\s/.test(line)) {
      const text = line.replace(/^\d+\.\s/, '')
      elements.push(
        <li key={i} className="ml-4 text-sm text-gray-700 list-decimal leading-relaxed">
          {formatInlineText(text)}
        </li>
      )
    }
    // Regular paragraph
    else if (line.trim()) {
      elements.push(
        <p key={i} className="text-sm text-gray-700 mb-1.5 leading-relaxed">
          {formatInlineText(line)}
        </p>
      )
    }
    // Empty line = spacing
    else {
      elements.push(<div key={i} className="h-1.5" />)
    }

    i++
  }

  return <div className="space-y-1">{elements}</div>
}

/**
 * Format inline text (bold, code)
 */
function formatInlineText(text) {
  // Split by bold markers
  const parts = text.split(/(\*\*[^*]+\*\*)/g)

  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={idx} className="font-semibold text-gray-900">
          {part.slice(2, -2)}
        </strong>
      )
    }
    // Inline code
    if (part.includes('`')) {
      const codeParts = part.split(/(`[^`]+`)/g)
      return codeParts.map((codePart, codeIdx) => {
        if (codePart.startsWith('`') && codePart.endsWith('`')) {
          return (
            <code key={`${idx}-${codeIdx}`} className="bg-gray-100/80 border border-gray-200/50 px-1.5 py-0.5 rounded text-xs font-mono">
              {codePart.slice(1, -1)}
            </code>
          )
        }
        return codePart
      })
    }
    return part
  })
}

export function ChatInterface({ className }) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'agent',
      content: `Hello I'm your very own **Expansion Agent**!

I can help your team achieve 5-min Hunger Satisfaction by answering questions on the following topics:
- Analyze current store performance
- Explore expansion opportunities
- Determine potential partnerships`,
      timestamp: new Date(),
    },
  ])

  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const {
    sendMessage: sendAgentMessage,
    connectionStatus,
    isAvailable,
    clearHistory,
  } = useExpansionAgent()

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (message = inputValue) => {
    if (!message.trim() || isLoading || !isAvailable) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: message.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const result = await sendAgentMessage(message)

      const agentMessage = {
        id: Date.now() + 1,
        type: 'agent',
        content: result.message,
        timestamp: new Date(),
        status: result.success ? 'delivered' : 'error',
      }

      setMessages((prev) => [...prev, agentMessage])
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'agent',
        content: `**Error**\n\n${error.message}`,
        timestamp: new Date(),
        status: 'error',
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleClearChat = () => {
    clearHistory()
    setMessages([
      {
        id: Date.now(),
        type: 'agent',
        content: '**Chat cleared!** Ready to help with expansion analysis. What would you like to explore?',
        timestamp: new Date(),
      },
    ])
  }

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <CheckCircle className="w-3 h-3 text-green-500" />
      case 'connecting':
        return <Clock className="w-3 h-3 text-yellow-500 animate-spin" />
      default:
        return <AlertCircle className="w-3 h-3 text-red-500" />
    }
  }

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected'
      case 'connecting':
        return 'Connecting...'
      case 'error':
        return 'Disconnected'
      default:
        return 'Not configured'
    }
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200/80 bg-gradient-to-br from-brand-orange via-red-700 to-red-800 text-white rounded-t-xl shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-white/10 rounded-lg">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm leading-tight">Expansion Agent</h3>
            <div className="flex items-center gap-1.5 text-[11px] opacity-90">
              {getStatusIcon()}
              <span>{getStatusText()}</span>
            </div>
          </div>
        </div>
        <button
          onClick={handleClearChat}
          className="p-1.5 hover:bg-white/15 rounded-lg transition-all duration-200 hover:scale-105"
          title="New chat"
        >
          <PlusCircle className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gradient-to-b from-gray-50/30 to-gray-50/70">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              'flex',
              message.type === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={cn(
                'max-w-[85%] rounded-2xl px-3.5 py-2.5 shadow-sm',
                message.type === 'user'
                  ? 'bg-gradient-to-br from-brand-orange to-red-700 text-white shadow-red-200/40 shadow-md'
                  : message.status === 'error'
                  ? 'bg-red-50 border border-red-200/70 text-red-800 shadow-red-100/50'
                  : 'bg-white border border-gray-200/70 text-gray-800 shadow-gray-200/40'
              )}
            >
              {message.type === 'agent' ? (
                <SimpleMarkdown content={message.content} />
              ) : (
                <p className="text-sm leading-relaxed">{message.content}</p>
              )}
              <div
                className={cn(
                  'text-[10px] mt-1.5 opacity-60',
                  message.type === 'user' ? 'text-red-100' : 'text-gray-500'
                )}
              >
                {message.timestamp.toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200/70 rounded-2xl px-3.5 py-2.5 shadow-sm shadow-gray-200/40">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 bg-brand-orange/70 rounded-full animate-bounce" />
                  <div
                    className="w-1.5 h-1.5 bg-brand-orange/70 rounded-full animate-bounce"
                    style={{ animationDelay: '0.1s' }}
                  />
                  <div
                    className="w-1.5 h-1.5 bg-brand-orange/70 rounded-full animate-bounce"
                    style={{ animationDelay: '0.2s' }}
                  />
                </div>
                <span className="text-xs text-gray-600 font-medium">Analyzing...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Questions */}
      {messages.length <= 1 && (
        <div className="px-3 py-2.5 border-t border-gray-200/80 bg-gradient-to-b from-gray-50/80 to-white">
          <p className="text-[11px] font-medium text-gray-600 mb-2">Try asking:</p>
          <div className="flex flex-col gap-1.5">
            {QUICK_QUESTIONS.map((question, idx) => (
              <button
                key={idx}
                onClick={() => sendMessage(question)}
                disabled={isLoading || !isAvailable}
                className="text-xs px-3 py-2 bg-white border border-gray-200/80 rounded-lg hover:border-brand-orange hover:bg-brand-orange/5 hover:shadow-sm disabled:opacity-50 transition-all duration-200 text-left hover:scale-[1.01]"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-gray-200/80 bg-white rounded-b-xl">
        <div className="flex gap-2 items-end">
          <div className="flex-1 border border-gray-200/80 rounded-xl bg-white shadow-sm focus-within:border-brand-orange/50 focus-within:ring-2 focus-within:ring-brand-orange/10 transition-all duration-200">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                isAvailable
                  ? 'Ask about expansion opportunities...'
                  : 'Connecting to analytics service...'
              }
              disabled={isLoading || !isAvailable}
              className="w-full resize-none border-none rounded-xl px-3 py-2 text-sm focus:outline-none disabled:bg-gray-50 disabled:cursor-not-allowed"
              rows="2"
            />
          </div>
          <button
            onClick={() => sendMessage()}
            disabled={isLoading || !inputValue.trim() || !isAvailable}
            className="p-2.5 bg-gradient-to-br from-brand-orange to-red-700 text-white rounded-xl hover:shadow-md hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all duration-200 flex items-center justify-center"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
