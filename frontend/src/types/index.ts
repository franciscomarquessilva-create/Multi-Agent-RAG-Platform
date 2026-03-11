export interface Agent {
  id: string
  name: string
  model: string
  is_orchestrator: boolean
  created_at: string
}

export interface AgentCreate {
  name: string
  model: string
  api_key: string
}

export interface AgentUpdate {
  name?: string
  model?: string
  api_key?: string
}

export interface Conversation {
  id: string
  title: string
  agent_ids: string[]
  created_at: string
  updated_at: string
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[]
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  mode: 'orchestrator' | 'slave' | null
  agent_id: string | null
  agent_name: string | null
  created_at: string
}

export type ChatMode = 'orchestrator' | 'slave'

export interface StreamChunk {
  agent: string
  content: string
  done: boolean
}

// Ephemeral message shown while streaming
export interface EphemeralMessage {
  agent: string
  content: string
  isStreaming: boolean
}
