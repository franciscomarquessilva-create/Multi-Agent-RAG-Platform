export interface Agent {
  id: string
  name: string
  model: string
  agent_type: 'orchestrator' | 'slave'
  purpose: string
  instructions: string
  orchestrator_mode: 'broadcast' | 'orchestrate' | null
  allowed_slave_ids: string[]
  orchestration_rules: OrchestrationRule[]
  is_orchestrator: boolean
  created_at: string
}

export interface OrchestrationRule {
  slave_agent_id: string
  rule: string
}

export interface AgentCreate {
  name: string
  model: string
  api_key: string
  agent_type: 'orchestrator' | 'slave'
  purpose: string
  instructions: string
  orchestrator_mode?: 'broadcast' | 'orchestrate'
  allowed_slave_ids: string[]
  orchestration_rules: OrchestrationRule[]
}

export interface AgentUpdate {
  name?: string
  model?: string
  api_key?: string
  agent_type?: 'orchestrator' | 'slave'
  purpose?: string
  instructions?: string
  orchestrator_mode?: 'broadcast' | 'orchestrate'
  allowed_slave_ids?: string[]
  orchestration_rules?: OrchestrationRule[]
}

export interface Conversation {
  id: string
  title: string
  orchestrator_id: string
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
  message_type: 'chat' | 'internal'
  mode: 'orchestrator' | null
  agent_id: string | null
  agent_name: string | null
  created_at: string
}

export type ChatMode = 'orchestrator'

export interface StreamChunk {
  agent: string
  content: string
  done: boolean
  message_type: 'chat' | 'internal'
  groupKey?: string
  isStreaming?: boolean
  processingTarget?: string
}

export interface StreamTraceEvent {
  stage: string
  details?: string
}

// Ephemeral message shown while streaming
export interface EphemeralMessage {
  key: string
  agent: string
  content: string
  message_type: 'chat' | 'internal'
  isStreaming: boolean
}

export interface PromptConfigItem {
  key: string
  value: string
  description: string
}

export interface LLMLog {
  id: string
  agent_id: string | null
  agent_name: string
  model: string
  request_payload: string
  response_payload: string | null
  error: string | null
  created_at: string
}

export interface ClientAuditTrace {
  id: string
  stage: string
  details: string | null
  conversation_id: string | null
  created_at: string
}

export interface ModelOption {
  provider: string
  label: string
  model: string
}

export interface AppSettings {
  allowed_models: string[]
  available_models: ModelOption[]
}
