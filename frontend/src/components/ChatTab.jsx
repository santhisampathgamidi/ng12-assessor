import React, { useState, useEffect, useRef } from 'react'
import { Send, RotateCcw, Paperclip, ChevronDown } from 'lucide-react'

const SUGGESTIONS = [
  "What symptoms trigger an urgent referral for lung cancer?",
  "Does persistent hoarseness require referral, and at what age?",
  "Summarize the referral criteria for visible haematuria",
  "What does NG12 say about dyspepsia thresholds?",
]

function TypewriterChat({ text, onComplete }) {
  const [displayed, setDisplayed] = useState('')
  const idx = useRef(0)

  useEffect(() => {
    idx.current = 0
    setDisplayed('')
    const interval = setInterval(() => {
      idx.current += 4
      if (idx.current >= text.length) {
        setDisplayed(text)
        clearInterval(interval)
        onComplete?.()
      } else {
        setDisplayed(text.slice(0, idx.current))
      }
    }, 6)
    return () => clearInterval(interval)
  }, [text])

  return <span dangerouslySetInnerHTML={{ __html: formatText(displayed) }} />
}

function formatText(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-blue-400">$1</strong>')
    .replace(/\[NG12(.*?)\]/g, '<strong class="text-blue-400">[NG12$1]</strong>')
    .replace(/\n/g, '<br/>')
}

export default function ChatTab() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(() => 'sess_' + Math.random().toString(36).substr(2, 9))
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(scrollToBottom, [messages, loading])

  const sendMessage = async (text) => {
    const msg = text || input.trim()
    if (!msg) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setLoading(true)

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: msg }),
      })

      if (!res.ok) throw new Error((await res.json()).detail || 'Chat failed')
      const data = await res.json()

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ Error: ${e.message}`,
        citations: [],
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // First-load state before the user sends a message.
  if (messages.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex-1 flex flex-col items-center justify-center gap-6 px-6">
          <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-blue-500 rounded-2xl flex items-center justify-center text-2xl">
            💬
          </div>
          <div className="text-center">
            <h2 className="text-xl font-bold tracking-tight mb-1">Ask about NG12 Guidelines</h2>
            <p className="text-gray-500 text-sm">Answers grounded in the NICE cancer referral guideline with citations</p>
          </div>
          <div className="grid grid-cols-2 gap-2.5 max-w-xl w-full">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => sendMessage(s)}
                className="bg-[#1a1a1a] border border-[#333] rounded-xl p-3.5 text-xs text-gray-400 text-left hover:border-blue-500/40 hover:text-gray-200 transition-all leading-relaxed"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
        <ChatInput
          input={input}
          setInput={setInput}
          onSend={sendMessage}
          onKey={handleKey}
          loading={loading}
          inputRef={inputRef}
        />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Conversation thread */}
      <div className="flex-1 overflow-y-auto py-6">
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} isLast={i === messages.length - 1 && msg.role === 'assistant'} />
        ))}

        {/* Assistant is fetching + generating */}
        {loading && (
          <div className="px-6 mb-6">
            <div className="max-w-2xl mx-auto flex gap-3">
              <div className="w-7 h-7 bg-gradient-to-br from-purple-500 to-blue-500 rounded-lg flex items-center justify-center text-xs shrink-0 mt-0.5">
                🏥
              </div>
              <div className="flex items-center gap-1.5 py-3">
                {[0, 1, 2].map(i => (
                  <div key={i} className="w-1.5 h-1.5 bg-gray-600 rounded-full typing-dot" />
                ))}
                <span className="text-xs text-gray-600 ml-1">Searching guidelines...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        input={input}
        setInput={setInput}
        onSend={sendMessage}
        onKey={handleKey}
        loading={loading}
        inputRef={inputRef}
      />
    </div>
  )
}

function Message({ msg, isLast }) {
  const [showCitations, setShowCitations] = useState(false)
  const isUser = msg.role === 'user'

  return (
    <div className="px-6 mb-6 animate-fade-up">
      <div className="max-w-2xl mx-auto flex gap-3">
        {/* Message avatar */}
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs shrink-0 mt-0.5 ${
          isUser
            ? 'bg-blue-600 text-white font-bold'
            : 'bg-gradient-to-br from-purple-500 to-blue-500'
        }`}>
          {isUser ? 'S' : '🏥'}
        </div>

        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-semibold text-gray-500 mb-1">
            {isUser ? 'You' : 'NG12 Assistant'}
          </div>
          <div className="text-sm leading-relaxed text-gray-200 whitespace-pre-wrap break-words">
            {isUser ? (
              msg.content
            ) : isLast ? (
              <TypewriterChat text={msg.content} />
            ) : (
              <span dangerouslySetInnerHTML={{ __html: formatText(msg.content) }} />
            )}
          </div>

          {/* Expandable evidence list */}
          {msg.citations?.length > 0 && (
            <div className="mt-2">
              <button
                onClick={() => setShowCitations(!showCitations)}
                className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 font-medium"
              >
                <Paperclip size={11} />
                {msg.citations.length} source(s)
                <ChevronDown size={11} className={`transition-transform ${showCitations ? 'rotate-180' : ''}`} />
              </button>
              {showCitations && (
                <div className="mt-2 space-y-1.5">
                  {msg.citations.map((c, i) => (
                    <div key={i} className="bg-[#0f0f0f] border border-[#333] rounded-lg p-2.5 text-[11px]">
                      <code className="font-mono text-blue-400 font-semibold">[{c.chunk_id}]</code>
                      <span className="text-gray-600 ml-1">Page {c.page}</span>
                      <p className="text-gray-600 mt-1 leading-relaxed line-clamp-2">
                        {c.excerpt?.substring(0, 150)}...
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ChatInput({ input, setInput, onSend, onKey, loading, inputRef }) {
  return (
    <div className="px-6 pb-6 pt-3 bg-gradient-to-t from-[#0f0f0f] via-[#0f0f0f] to-transparent">
      <div className="max-w-2xl mx-auto">
        <div className="bg-[#1a1a1a] border border-[#333] rounded-2xl flex items-end p-2 focus-within:border-blue-500/50 focus-within:ring-2 focus-within:ring-blue-500/10 transition-all">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKey}
            rows={1}
            placeholder="Ask about NG12 guidelines..."
            className="flex-1 bg-transparent border-none text-sm px-3 py-2 resize-none max-h-28 focus:outline-none placeholder:text-gray-600"
            style={{ height: 'auto', minHeight: '36px' }}
            onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 112) + 'px' }}
          />
          <button
            onClick={() => onSend()}
            disabled={!input.trim() || loading}
            className="w-8 h-8 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:opacity-40 text-white flex items-center justify-center transition-all shrink-0"
          >
            <Send size={14} />
          </button>
        </div>
        <p className="text-center text-[10px] text-gray-600 mt-2">
          Grounded in NICE NG12 guideline with citations
        </p>
      </div>
    </div>
  )
}
