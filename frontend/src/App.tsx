import { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar/Sidebar'
import Chat from './components/Chat/Chat'
import AgentManager from './components/AgentManager/AgentManager'
import Audit from './components/Audit/Audit'
import Settings from './components/Settings/Settings'
import NewConversationModal from './modals/NewConversationModal'
import type { AppSettings, Conversation, Agent, ConversationWithMessages, Message, EphemeralMessage, PromptConfigItem } from './types'
import { getAgents, getAppSettings, getConversations, createConversation, getConversation, deleteConversation, sendMessageStream, getPromptConfigs } from './services/api'
import { appendClientAuditTrace } from './services/auditTrace'

type View = 'chat' | 'agents' | 'audit' | 'settings'

export default function App() {
  const [view, setView] = useState<View>('chat')
  const [agents, setAgents] = useState<Agent[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversation, setActiveConversation] = useState<ConversationWithMessages | null>(null)
  const [showNewConvModal, setShowNewConvModal] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [ephemeral, setEphemeral] = useState<Record<string, EphemeralMessage>>({})
  const [processingTargets, setProcessingTargets] = useState<string[]>([])
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [promptConfigs, setPromptConfigs] = useState<PromptConfigItem[]>([])

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

  const loadSettings = useCallback(async () => {
    try {
      const data = await getAppSettings()
      setSettings(data)
    } catch (e) {
      console.error('Failed to load settings', e)
    }
  }, [])

  const loadPromptConfigs = useCallback(async () => {
    try {
      const data = await getPromptConfigs()
      setPromptConfigs(data)
    } catch (e) {
      console.error('Failed to load prompt configs', e)
    }
  }, [])

  useEffect(() => {
    loadAgents()
    loadConversations()
    loadSettings()
    loadPromptConfigs()
  }, [loadAgents, loadConversations, loadSettings, loadPromptConfigs])

  const handleSelectConversation = async (conv: Conversation) => {
    try {
      const full = await getConversation(conv.id)
      setActiveConversation(full)
      setEphemeral({})
      setProcessingTargets([])
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

  const handleConversationCreated = async (orchestratorId: string, agentIds: string[]) => {
    setShowNewConvModal(false)
    try {
      const conv = await createConversation('New Conversation', orchestratorId, agentIds)
      setConversations(prev => [conv, ...prev])
      const full = await getConversation(conv.id)
      setActiveConversation(full)
      setEphemeral({})
      setProcessingTargets([])
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

  const handleSendMessage = ({
    content,
    iterations = 1,
    broadcastInstructions,
    orchestratorInstructions,
  }: {
    content: string
    iterations?: number
    broadcastInstructions?: string
    orchestratorInstructions?: string
  }) => {
    if (!activeConversation) {
      appendClientAuditTrace({
        stage: 'app.send.blocked',
        details: 'No active conversation selected',
        conversation_id: null,
      })
      return
    }
    if (streaming) {
      appendClientAuditTrace({
        stage: 'app.send.blocked',
        details: 'Streaming already in progress',
        conversation_id: activeConversation.id,
      })
      return
    }

    const trace = (stage: string, details?: string) => {
      appendClientAuditTrace({
        stage,
        details: details ?? null,
        conversation_id: activeConversation.id,
      })
    }

    trace(
      'app.send.accepted',
      `content_len=${content.length} broadcast_len=${broadcastInstructions?.length ?? 0} orchestrator_len=${orchestratorInstructions?.length ?? 0}`,
    )

    const conversationOrchestrator = agents.find(a => a.id === activeConversation.orchestrator_id)
    setProcessingTargets(conversationOrchestrator ? [conversationOrchestrator.name] : ['Orchestrator'])

    // Optimistically add user message
    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversation.id,
      role: 'user',
      content,
      message_type: 'chat',
      mode: 'orchestrator',
      agent_id: null,
      agent_name: null,
      created_at: new Date().toISOString(),
    }
    setActiveConversation(prev => prev ? { ...prev, messages: [...prev.messages, userMsg] } : prev)
    setEphemeral({})
    setStreaming(true)
    trace('app.streaming.started')

    let streamChunkCount = 0

    sendMessageStream(
      {
        conversationId: activeConversation.id,
        content,
        iterations,
        broadcastInstructions,
        orchestratorInstructions,
      },
      (streamChunk) => {
        streamChunkCount += 1
        if (streamChunkCount === 1 || streamChunkCount % 20 === 0) {
          trace(
            'app.stream.chunk',
            `index=${streamChunkCount} agent=${streamChunk.agent || 'unknown'} type=${streamChunk.message_type} len=${streamChunk.content.length}`,
          )
        }
        const chunkKey = streamChunk.groupKey || streamChunk.agent
        const processingTarget = streamChunk.processingTarget || streamChunk.agent

        if (processingTarget) {
          setProcessingTargets(prev => prev.filter(name => !(processingTarget === name || processingTarget.startsWith(`${name} ·`))))
        }
        setEphemeral(prev => {
          const existing = prev[chunkKey] || {
            key: chunkKey,
            agent: streamChunk.agent,
            content: '',
            message_type: streamChunk.message_type,
            isStreaming: Boolean(streamChunk.isStreaming),
          }
          return {
            ...prev,
            [chunkKey]: {
              ...existing,
              agent: streamChunk.agent,
              message_type: streamChunk.message_type,
              content: existing.content + streamChunk.content,
              isStreaming: Boolean(streamChunk.isStreaming),
            },
          }
        })
      },
      async () => {
        trace('app.stream.done', `chunks=${streamChunkCount}`)
        setStreaming(false)
        setEphemeral({})
        setProcessingTargets([])
        // Reload conversation to get persisted messages
        try {
          const refreshed = await getConversation(activeConversation.id)
          setActiveConversation(refreshed)
          // Update conversation title in sidebar
          setConversations(prev =>
            prev.map(c => c.id === refreshed.id ? { ...c, title: refreshed.title, updated_at: refreshed.updated_at } : c)
          )
          trace('app.conversation.refreshed', `messages=${refreshed.messages.length}`)
        } catch (e) {
          console.error('Failed to refresh conversation', e)
          trace('app.conversation.refresh_error', e instanceof Error ? e.message : String(e))
        }
      },
      (err) => {
        trace('app.stream.error', err.message)
        setStreaming(false)
        setEphemeral({})
        setProcessingTargets([])
        console.error('Stream error', err)
        const errorMsg: Message = {
          id: `error-${Date.now()}`,
          conversation_id: activeConversation.id,
          role: 'system',
          content: `Request failed: ${err.message}`,
          message_type: 'chat',
          mode: 'orchestrator',
          agent_id: null,
          agent_name: 'System',
          created_at: new Date().toISOString(),
        }
        setActiveConversation(prev => prev ? { ...prev, messages: [...prev.messages, errorMsg] } : prev)
      },
      (event) => {
        trace(`transport.${event.stage}`, event.details)
      }
    )
  }

  const slaveAgents = agents.filter(a => a.agent_type === 'slave')

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversation?.id}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onManageAgents={() => setView('agents')}
        onOpenSettings={() => setView('settings')}
        onOpenAudit={() => setView('audit')}
      />

      <main className="flex-1 overflow-hidden">
        {view === 'agents' ? (
          <AgentManager
            agents={agents}
            allowedModels={settings?.allowed_models ?? []}
            promptConfigs={promptConfigs}
            onAgentsChanged={loadAgents}
            onBack={() => setView('chat')}
          />
        ) : view === 'settings' ? (
          <Settings
            settings={settings}
            promptConfigs={promptConfigs}
            onSettingsChanged={setSettings}
            onPromptsChanged={setPromptConfigs}
            onBack={() => setView('chat')}
          />
        ) : view === 'audit' ? (
          <Audit onBack={() => setView('chat')} />
        ) : (
          <Chat
            conversation={activeConversation}
            ephemeral={ephemeral}
            processingTargets={processingTargets}
            streaming={streaming}
            agents={agents}
            slaveAgents={slaveAgents}
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
