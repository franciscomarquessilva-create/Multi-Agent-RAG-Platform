import { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar/Sidebar'
import Chat from './components/Chat/Chat'
import AgentManager from './components/AgentManager/AgentManager'
import NewConversationModal from './modals/NewConversationModal'
import type { Conversation, Agent, ConversationWithMessages, Message, EphemeralMessage, ChatMode } from './types'
import { getAgents, getConversations, createConversation, getConversation, deleteConversation, sendMessageStream } from './services/api'

type View = 'chat' | 'agents'

export default function App() {
  const [view, setView] = useState<View>('chat')
  const [agents, setAgents] = useState<Agent[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversation, setActiveConversation] = useState<ConversationWithMessages | null>(null)
  const [showNewConvModal, setShowNewConvModal] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [ephemeral, setEphemeral] = useState<Record<string, EphemeralMessage>>({})

  const loadAgents = useCallback(async () => {
    try {
      const data = await getAgents()
      setAgents(data)
    } catch (e) {
      console.error('Failed to load agents', e)
    }
  }, [])

  const loadConversations = useCallback(async () => {
    try {
      const data = await getConversations()
      setConversations(data)
    } catch (e) {
      console.error('Failed to load conversations', e)
    }
  }, [])

  useEffect(() => {
    loadAgents()
    loadConversations()
  }, [loadAgents, loadConversations])

  const handleSelectConversation = async (conv: Conversation) => {
    try {
      const full = await getConversation(conv.id)
      setActiveConversation(full)
      setEphemeral({})
      setView('chat')
    } catch (e) {
      console.error('Failed to load conversation', e)
    }
  }

  const handleNewConversation = () => {
    if (agents.length === 0) {
      setView('agents')
      return
    }
    setShowNewConvModal(true)
  }

  const handleConversationCreated = async (agentIds: string[]) => {
    setShowNewConvModal(false)
    try {
      const conv = await createConversation('New Conversation', agentIds)
      setConversations(prev => [conv, ...prev])
      const full = await getConversation(conv.id)
      setActiveConversation(full)
      setEphemeral({})
      setView('chat')
    } catch (e) {
      console.error('Failed to create conversation', e)
    }
  }

  const handleDeleteConversation = async (convId: string) => {
    try {
      await deleteConversation(convId)
      setConversations(prev => prev.filter(c => c.id !== convId))
      if (activeConversation?.id === convId) {
        setActiveConversation(null)
      }
    } catch (e) {
      console.error('Failed to delete conversation', e)
    }
  }

  const handleSendMessage = (content: string, mode: ChatMode, agentIds?: string[]) => {
    if (!activeConversation || streaming) return

    // Optimistically add user message
    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversation.id,
      role: 'user',
      content,
      mode,
      agent_id: null,
      agent_name: null,
      created_at: new Date().toISOString(),
    }
    setActiveConversation(prev => prev ? { ...prev, messages: [...prev.messages, userMsg] } : prev)
    setEphemeral({})
    setStreaming(true)

    sendMessageStream(
      { conversationId: activeConversation.id, content, mode, agentIds },
      (agent, chunk) => {
        setEphemeral(prev => {
          const existing = prev[agent] || { agent, content: '', isStreaming: true }
          return {
            ...prev,
            [agent]: { ...existing, content: existing.content + chunk, isStreaming: true },
          }
        })
      },
      async () => {
        setStreaming(false)
        setEphemeral({})
        // Reload conversation to get persisted messages
        try {
          const refreshed = await getConversation(activeConversation.id)
          setActiveConversation(refreshed)
          // Update conversation title in sidebar
          setConversations(prev =>
            prev.map(c => c.id === refreshed.id ? { ...c, title: refreshed.title, updated_at: refreshed.updated_at } : c)
          )
        } catch (e) {
          console.error('Failed to refresh conversation', e)
        }
      },
      (err) => {
        setStreaming(false)
        setEphemeral({})
        console.error('Stream error', err)
      }
    )
  }

  const slaveAgents = agents.filter(a => !a.is_orchestrator)
  const orchestrator = agents.find(a => a.is_orchestrator)

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversation?.id}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onManageAgents={() => setView('agents')}
      />

      <main className="flex-1 overflow-hidden">
        {view === 'agents' ? (
          <AgentManager
            agents={agents}
            onAgentsChanged={loadAgents}
            onBack={() => setView('chat')}
          />
        ) : (
          <Chat
            conversation={activeConversation}
            ephemeral={ephemeral}
            streaming={streaming}
            agents={agents}
            slaveAgents={slaveAgents}
            orchestrator={orchestrator}
            onSend={handleSendMessage}
            onNewConversation={handleNewConversation}
          />
        )}
      </main>

      {showNewConvModal && (
        <NewConversationModal
          agents={agents}
          onConfirm={handleConversationCreated}
          onCancel={() => setShowNewConvModal(false)}
        />
      )}
    </div>
  )
}
