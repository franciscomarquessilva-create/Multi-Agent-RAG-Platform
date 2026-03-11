import React, { useState } from 'react'
import { Send, Users, Bot } from 'lucide-react'
import type { ChatMode, Agent } from '../../types'

interface Props {
  mode: ChatMode
  onModeChange: (mode: ChatMode) => void
  onSend: (content: string, agentIds?: string[]) => void
  disabled: boolean
  slaveAgents: Agent[]
  selectedAgentIds: string[]
  onSelectedAgentsChange: (ids: string[]) => void
}

export default function InputBar({
  mode,
  onModeChange,
  onSend,
  disabled,
  slaveAgents,
  selectedAgentIds,
  onSelectedAgentsChange,
}: Props) {
  const [text, setText] = useState('')
  const [showAgentPicker, setShowAgentPicker] = useState(false)

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed, mode === 'slave' ? selectedAgentIds : undefined)
    setText('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const toggleAgent = (id: string) => {
    onSelectedAgentsChange(
      selectedAgentIds.includes(id)
        ? selectedAgentIds.filter(a => a !== id)
        : [...selectedAgentIds, id]
    )
  }

  return (
    <div className="border-t border-gray-700 px-4 py-3 bg-gray-800">
      {/* Mode toggle */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-gray-400">Instruction target:</span>
        <div className="flex rounded-lg overflow-hidden border border-gray-600">
          <button
            onClick={() => onModeChange('orchestrator')}
            className={`flex items-center gap-1 px-3 py-1 text-xs transition-colors ${
              mode === 'orchestrator'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            <Bot size={12} />
            Orchestrator
          </button>
          <button
            onClick={() => onModeChange('slave')}
            className={`flex items-center gap-1 px-3 py-1 text-xs transition-colors ${
              mode === 'slave'
                ? 'bg-emerald-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            <Users size={12} />
            Slave Agents
          </button>
        </div>

        {/* Agent selector for slave mode */}
        {mode === 'slave' && slaveAgents.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setShowAgentPicker(p => !p)}
              className="text-xs px-2 py-1 rounded border border-gray-600 bg-gray-700 hover:bg-gray-600 text-gray-300"
            >
              Agents ({selectedAgentIds.length}/{slaveAgents.length})
            </button>
            {showAgentPicker && (
              <div className="absolute bottom-8 left-0 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-10 min-w-40">
                {slaveAgents.map(agent => (
                  <label key={agent.id} className="flex items-center gap-2 px-3 py-2 hover:bg-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedAgentIds.includes(agent.id)}
                      onChange={() => toggleAgent(agent.id)}
                      className="accent-emerald-500"
                    />
                    <span className="text-sm text-gray-200">{agent.name}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            mode === 'orchestrator'
              ? 'Message the orchestrator...'
              : 'Broadcast to slave agents...'
          }
          disabled={disabled}
          rows={1}
          className="flex-1 bg-gray-700 text-gray-100 placeholder-gray-500 rounded-xl px-4 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 max-h-32 overflow-y-auto"
          style={{ minHeight: '40px' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="p-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
