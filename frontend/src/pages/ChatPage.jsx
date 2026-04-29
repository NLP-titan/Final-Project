import React, { useState, useEffect, useRef } from 'react'
import { Menu, X, Send, MessageSquare, FileText, Plus, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { conversationsApi } from '../api/conversations.js'

function extractSource(toolCalls) {
  if (!toolCalls || toolCalls.length === 0) return null
  for (const call of toolCalls) {
    if (call.name === 'policy_retriever') {
      const chunks = call.output?.chunks
      if (chunks && chunks.length > 0) {
        const src = chunks[0].metadata?.source_file || chunks[0].source_file
        if (src) return src.replace(/^\d+_/, '').replace(/_/g, ' ').replace('.md', '')
      }
    }
    if (call.name === 'medicines_checker' && call.output?.summary) {
      return 'NHIS Medicines Formulary'
    }
    if (call.name === 'facility_checker' && call.output?.summary) {
      return 'NHIS Accredited Facilities Directory'
    }
  }
  return 'NHIS Policy Knowledge Base'
}

const WELCOME = {
  role: 'assistant',
  content: 'Hello. I am the NHIS Rights & Entitlement Agent. I can help you check drug coverage, find facilities, or understand your rights as a patient. What do you need help with?',
  tool_calls: [],
  suggestions: ['Is dialysis covered under NHIS?', 'Find an accredited hospital near me', 'They charged me for Paracetamol. Is that right?'],
}

export default function ChatPage() {
  const [conversations, setConversations] = useState([])
  const [activeConvId, setActiveConvId] = useState(null)
  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [convLoading, setConvLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    conversationsApi.list().then(setConversations).catch(() => {})
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadConversation = async (conv) => {
    setConvLoading(true)
    setSidebarOpen(false)
    try {
      const detail = await conversationsApi.get(conv.id)
      setActiveConvId(conv.id)
      if (detail.messages.length === 0) {
        setMessages([WELCOME])
      } else {
        setMessages(detail.messages)
      }
    } catch {
      setMessages([WELCOME])
    } finally {
      setConvLoading(false)
    }
  }

  const startNewChat = () => {
    setActiveConvId(null)
    setMessages([WELCOME])
    setSidebarOpen(false)
  }

  const deleteConversation = async (e, convId) => {
    e.stopPropagation()
    try {
      await conversationsApi.delete(convId)
      setConversations(prev => prev.filter(c => c.id !== convId))
      if (activeConvId === convId) startNewChat()
    } catch {}
  }

  const sendMessage = async (text) => {
    const userText = (text || input).trim()
    if (!userText || loading) return

    setInput('')
    setLoading(true)

    const userMsg = { role: 'user', content: userText, tool_calls: [] }
    setMessages(prev => [...prev.filter(m => !m.suggestions), userMsg])

    try {
      let convId = activeConvId
      if (!convId) {
        const conv = await conversationsApi.create(userText.slice(0, 60))
        convId = conv.id
        setActiveConvId(convId)
        setConversations(prev => [conv, ...prev])
      }

      const res = await conversationsApi.sendMessage(convId, userText)
      setMessages(prev => [...prev, res.assistant_message])

      // Refresh sidebar title
      setConversations(prev => prev.map(c =>
        c.id === convId ? { ...c, title: c.title || userText.slice(0, 60), message_count: c.message_count + 2 } : c
      ))
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'I am currently unable to reach the server. Please check that the backend is running, or contact NHIS directly on 0800-900-9900.',
        tool_calls: [],
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => { e?.preventDefault(); sendMessage() }

  return (
    <div className="bg-white rounded-2xl border border-slate-100 flex flex-row h-[80vh] overflow-hidden shadow-sm relative">

      {/* Sidebar Overlay (mobile) */}
      {sidebarOpen && (
        <div className="absolute inset-0 bg-black/20 z-20 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <div className={`absolute md:relative z-30 w-64 h-full bg-slate-50 border-r border-slate-100 flex flex-col transition-transform duration-300 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className="p-5 border-b border-slate-200 flex justify-between items-center">
          <h3 className="font-bold text-slate-800">History</h3>
          <button onClick={() => setSidebarOpen(false)} className="md:hidden text-slate-400 hover:text-slate-800"><X size={20} /></button>
        </div>
        <div className="p-3">
          <button onClick={startNewChat}
            className="w-full flex items-center justify-center gap-2 bg-white border border-slate-200 text-[#3454D1] py-2 rounded-lg font-semibold text-sm hover:bg-blue-50 transition-colors shadow-sm mb-4">
            <Plus size={16} /> New Chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 pb-4">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 px-2">Recent</p>
          <div className="flex flex-col gap-1">
            {conversations.map(conv => (
              <div key={conv.id}
                onClick={() => loadConversation(conv)}
                className={`px-3 py-2.5 rounded-lg hover:bg-slate-200 cursor-pointer transition-colors group flex items-center justify-between ${activeConvId === conv.id ? 'bg-blue-50' : ''}`}>
                <div className="overflow-hidden">
                  <p className={`text-sm font-semibold truncate group-hover:text-[#3454D1] ${activeConvId === conv.id ? 'text-[#3454D1]' : 'text-slate-700'}`}>
                    {conv.title || 'Untitled'}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {new Date(conv.updated_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                  </p>
                </div>
                <button onClick={(e) => deleteConversation(e, conv.id)} className="text-slate-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all shrink-0 ml-2">
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Chat */}
      <div className="flex-1 flex flex-col h-full bg-white relative">
        {/* Header */}
        <div className="border-b border-slate-100 p-4 bg-white flex items-center gap-4 shrink-0">
          <button onClick={() => setSidebarOpen(true)} className="md:hidden p-2 -ml-2 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-50">
            <Menu size={20} />
          </button>
          <div className="w-10 h-10 md:w-12 md:h-12 bg-blue-50 rounded-xl flex items-center justify-center shrink-0">
            <MessageSquare size={20} className="text-[#3454D1]" />
          </div>
          <div>
            <h2 className="font-bold text-slate-800 text-base md:text-lg">NHIS Policy Agent</h2>
            <p className="text-[11px] md:text-xs text-emerald-600 font-medium flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 block" />
              Grounded in Official Policy
            </p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-grow overflow-y-auto p-4 md:p-6 flex flex-col gap-6 bg-slate-50/30">
          {convLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-slate-400 text-sm">Loading conversation...</div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`
                  max-w-[90%] md:max-w-[75%] p-4 text-sm md:text-base leading-relaxed rounded-2xl
                  ${msg.role === 'user'
                    ? 'bg-[#3454D1] text-white rounded-br-sm shadow-sm'
                    : 'bg-white border border-slate-200 text-slate-800 shadow-sm rounded-bl-sm'}
                `}>
                  {msg.role === 'user' ? msg.content : (
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                        ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>,
                        li: ({ children }) => <li>{children}</li>,
                        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                        h1: ({ children }) => <h1 className="font-bold text-base mb-1">{children}</h1>,
                        h2: ({ children }) => <h2 className="font-bold text-sm mb-1">{children}</h2>,
                        h3: ({ children }) => <h3 className="font-semibold text-sm mb-1">{children}</h3>,
                        code: ({ children }) => <code className="bg-slate-100 px-1 rounded text-xs font-mono">{children}</code>,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  )}
                </div>

                {msg.role === 'assistant' && msg.role !== 'user' && (() => {
                  const src = extractSource(msg.tool_calls)
                  return src ? (
                    <div className="mt-2 text-[11px] md:text-xs font-medium text-slate-500 flex items-center gap-1 ml-1 bg-white border border-slate-100 px-2.5 py-1 rounded-md shadow-sm">
                      <FileText size={12} className="text-[#3454D1]" />
                      Source: {src}
                    </div>
                  ) : null
                })()}

                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-4">
                    {msg.suggestions.map((s, idx) => (
                      <button key={idx} onClick={() => sendMessage(s)}
                        className="text-xs font-medium border border-slate-200 bg-white text-slate-600 px-4 py-2.5 rounded-full hover:border-[#3454D1] hover:text-[#3454D1] hover:shadow-sm transition-all">
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}

          {loading && (
            <div className="flex items-start">
              <div className="bg-white border border-slate-200 text-slate-500 rounded-2xl rounded-bl-sm p-4 text-sm font-medium flex items-center gap-3 shadow-sm">
                <div className="flex gap-1.5">
                  <span className="w-1.5 h-1.5 bg-[#3454D1] rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-[#3454D1] rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <span className="w-1.5 h-1.5 bg-[#3454D1] rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
                Searching knowledge base...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-slate-200 p-4 bg-white shrink-0">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input type="text" value={input} onChange={e => setInput(e.target.value)}
              placeholder="Type your question about NHIS policy..."
              className="flex-grow border border-slate-200 rounded-xl p-3.5 focus:outline-none focus:ring-2 focus:ring-[#3454D1] focus:border-transparent text-slate-800 text-sm shadow-sm"
              disabled={loading} />
            <button type="submit" disabled={loading || !input.trim()}
              className="bg-[#3454D1] text-white px-5 rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center justify-center shadow-sm">
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
