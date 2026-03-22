import MessageList from './MessageList'
import InputBar from './InputBar'
import type { ConversationWithMessages, EphemeralMessage, Agent } from '../../types'
import { MessageSquare } from 'lucide-react'

interface Props {
  conversation: ConversationWithMessages | null
  ephemeral: Record<string, EphemeralMessage>
  processingTargets?: string[]
  streaming: boolean
  agents: Agent[]
  slaveAgents: Agent[]
  onSend: (payload: { content: string; iterations?: number; broadcastInstructions?: string; orchestratorInstructions?: string }) => void
  onNewConversation: () => void
}

export default function Chat({
  conversation,
  ephemeral,
  processingTargets = [],
  streaming,
  agents,
  slaveAgents,
  onSend,
  onNewConversation,
}: Props) {
  const handleSend = (payload: { content: string; iterations?: number; broadcastInstructions?: string; orchestratorInstructions?: string }) => onSend(payload)

  const conversationOrchestrator = conversation
    ? agents.find(a => a.id === conversation.orchestrator_id)
    : undefined

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
        {conversationOrchestrator && (
          <p className="text-xs text-gray-500">
            <span className="text-blue-400">{conversationOrchestrator.name}</span>
            {' · '}
            {slaveAgents.length} slave agent{slaveAgents.length !== 1 ? 's' : ''}
          </p>
        )}
        {streaming && processingTargets.length > 0 && (
          <p className="text-xs text-amber-300 mt-1">
            Processing: {processingTargets.join(', ')}
          </p>
        )}
      </div>

      <MessageList messages={conversation.messages} ephemeral={ephemeral} processingTargets={processingTargets} />

      <InputBar
        orchestratorMode={conversationOrchestrator?.orchestrator_mode}
        onSend={handleSend}
        disabled={streaming}
      />
    </div>
  )
}
