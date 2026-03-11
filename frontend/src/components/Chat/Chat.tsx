import { useState, useEffect } from 'react'
import MessageList from './MessageList'
import InputBar from './InputBar'
import type { ConversationWithMessages, EphemeralMessage, ChatMode, Agent } from '../../types'
import { MessageSquare } from 'lucide-react'

interface Props {
  conversation: ConversationWithMessages | null
  ephemeral: Record<string, EphemeralMessage>
  streaming: boolean
  agents: Agent[]
  slaveAgents: Agent[]
  orchestrator?: Agent
  onSend: (content: string, mode: ChatMode, agentIds?: string[]) => void
  onNewConversation: () => void
}

export default function Chat({
  conversation,
  ephemeral,
  streaming,
  agents,
  slaveAgents,
  orchestrator,
  onSend,
  onNewConversation,
}: Props) {
  const [mode, setMode] = useState<ChatMode>('orchestrator')
  const [selectedAgentIds, setSelectedAgentIds] = useState<string[]>([])

  // Auto-select slave agents from conversation
  useEffect(() => {
    if (conversation) {
      const ids = conversation.agent_ids.filter(id =>
        slaveAgents.some(a => a.id === id)
      )
      setSelectedAgentIds(ids)
    }
  }, [conversation?.id, slaveAgents])

  const handleSend = (content: string, agentIds?: string[]) => {
    onSend(content, mode, agentIds)
  }

  if (!conversation) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4">
        <MessageSquare size={48} className="text-gray-600 mb-4" />
        <h2 className="text-xl font-semibold text-gray-300 mb-2">Multi-Agent RAG</h2>
        <p className="text-gray-500 mb-6 max-w-md">
          Start a new conversation to interact with your AI agents.
          {agents.length === 0 && ' First, add some agents in the settings.'}
        </p>
        <button
          onClick={onNewConversation}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
        >
          {agents.length === 0 ? 'Add Agents' : 'New Conversation'}
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700 bg-gray-800">
        <h3 className="font-medium text-gray-200 truncate">{conversation.title}</h3>
        {orchestrator && (
          <p className="text-xs text-gray-500">
            Orchestrator: <span className="text-blue-400">{orchestrator.name}</span>
            {' · '}
            {slaveAgents.length} slave agent{slaveAgents.length !== 1 ? 's' : ''}
          </p>
        )}
      </div>

      <MessageList messages={conversation.messages} ephemeral={ephemeral} />

      <InputBar
        mode={mode}
        onModeChange={setMode}
        onSend={handleSend}
        disabled={streaming}
        slaveAgents={slaveAgents}
        selectedAgentIds={selectedAgentIds}
        onSelectedAgentsChange={setSelectedAgentIds}
      />
    </div>
  )
}
