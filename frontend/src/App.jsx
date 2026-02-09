import React, { useState } from 'react'
import { ClipboardCheck, MessageCircle } from 'lucide-react'
import AssessmentTab from './components/AssessmentTab'
import ChatTab from './components/ChatTab'

export default function App() {
  const [activeTab, setActiveTab] = useState('assess')

  return (
    <div className="flex flex-col h-screen">
      {/* Top bar */}
      <header className="bg-[#1a1a1a] border-b border-[#333] px-6 h-14 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center text-sm">
            🏥
          </div>
          <h1 className="text-sm font-semibold tracking-tight">NG12 Assessor</h1>
          <span className="text-[10px] font-semibold text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full">
            NICE NG12
          </span>
        </div>

        <div className="flex bg-[#0f0f0f] rounded-lg p-0.5 gap-0.5">
          <button
            onClick={() => setActiveTab('assess')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'assess'
                ? 'bg-[#222] text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <ClipboardCheck size={14} /> Assessment
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'chat'
                ? 'bg-[#222] text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <MessageCircle size={14} /> Chat
          </button>
        </div>
      </header>

      {/* Active tab body */}
      <main className="flex-1 overflow-hidden">
        {activeTab === 'assess' ? <AssessmentTab /> : <ChatTab />}
      </main>
    </div>
  )
}
