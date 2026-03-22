import axios from 'axios'
import type { Agent, AgentCreate, AgentUpdate, AppSettings, Conversation, ConversationWithMessages, CurrentUser, LLMLog, PromptConfigItem, StreamChunk, StreamTraceEvent, UserSummary, UserUpdate } from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const api = axios.create({ baseURL: BASE_URL })

// Impersonation support: AuthContext calls this to set/clear the header globally.
export function setImpersonationHeader(userId: string | null) {
  if (userId) {
    api.defaults.headers.common['X-Impersonate-User-Id'] = userId
  } else {
    delete api.defaults.headers.common['X-Impersonate-User-Id']
  }
}

// Agents
export const getAgents = () => api.get<Agent[]>('/agents').then(r => r.data)
export const createAgent = (data: AgentCreate) => api.post<Agent>('/agents', data).then(r => r.data)
export const updateAgent = (id: string, data: AgentUpdate) => api.put<Agent>(`/agents/${id}`, data).then(r => r.data)
export const deleteAgent = (id: string) => api.delete(`/agents/${id}`)
export const setOrchestrator = (id: string) => api.patch<Agent>(`/agents/${id}/orchestrator`).then(r => r.data)

// Conversations
export const getConversations = () => api.get<Conversation[]>('/conversations').then(r => r.data)
export const createConversation = (title: string, orchestratorId: string, agentIds: string[]) =>
  api.post<Conversation>('/conversations', { title, orchestrator_id: orchestratorId, agent_ids: agentIds }).then(r => r.data)
export const getConversation = (id: string) =>
  api.get<ConversationWithMessages>(`/conversations/${id}`).then(r => r.data)
export const deleteConversation = (id: string) => api.delete(`/conversations/${id}`)

// LLM logs
export const getLlmLogs = (limit = 200) =>
  api.get<LLMLog[]>(`/logs/llm?limit=${limit}`).then(r => r.data)

// Settings
export const getAppSettings = () => api.get<AppSettings>('/settings').then(r => r.data)
export const updateAppSettings = (creditsPerProcess?: number) =>
  api.put<AppSettings>('/settings', { credits_per_process: creditsPerProcess }).then(r => r.data)
export const setDefaultKey = (provider: string, apiKey: string) =>
  api.post<AppSettings>('/settings/default-keys', { provider, api_key: apiKey }).then(r => r.data)
export const deleteDefaultKey = (provider: string) =>
  api.delete<AppSettings>('/settings/default-keys', { params: { provider } }).then(r => r.data)
export const addSettingsModel = (payload: { provider: string; label: string; model: string; enabled: boolean }) =>
  api.post<AppSettings>('/settings/models', payload).then(r => r.data)
export const updateSettingsModel = (payload: { current_model: string; provider: string; label: string; model: string; enabled: boolean }) =>
  api.put<AppSettings>('/settings/models', payload).then(r => r.data)
export const deleteSettingsModel = (model: string) =>
  api.delete<AppSettings>('/settings/models', { params: { model } }).then(r => r.data)

// Prompt configs
export const getPromptConfigs = () => api.get<PromptConfigItem[]>('/settings/prompts').then(r => r.data)
export const updatePromptConfig = (key: string, value: string) =>
  api.put<PromptConfigItem>(`/settings/prompts/${key}`, { value }).then(r => r.data)

// Users / Auth
export const getMe = () => api.get<CurrentUser>('/users/me').then(r => r.data)
export const listUsers = () => api.get<UserSummary[]>('/users').then(r => r.data)
export const updateUser = (id: string, data: UserUpdate) =>
  api.patch<UserSummary>(`/users/${id}`, data).then(r => r.data)

// Chat streaming
export interface SendMessageParams {
  conversationId: string
  content: string
  broadcastInstructions?: string
  orchestratorInstructions?: string
  iterations?: number
}

export const sendMessageStream = (
  params: SendMessageParams,
  onChunk: (chunk: StreamChunk) => void,
  onDone: () => void,
  onError: (err: Error) => void,
  onTrace?: (event: StreamTraceEvent) => void
): (() => void) => {
  const emitTrace = (stage: string, details?: string) => {
    onTrace?.({ stage, details })
  }

  const controller = new AbortController()
  emitTrace('request.start', `conversation_id=${params.conversationId} iterations=${params.iterations ?? 1}`)

  const extraHeaders: Record<string, string> = {}
  const impersonateId = api.defaults.headers.common['X-Impersonate-User-Id']
  if (typeof impersonateId === 'string') extraHeaders['X-Impersonate-User-Id'] = impersonateId

  fetch(`${BASE_URL}/chat/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
    body: JSON.stringify({
      conversation_id: params.conversationId,
      content: params.content,
      broadcast_instructions: params.broadcastInstructions,
      orchestrator_instructions: params.orchestratorInstructions,
      mode: 'orchestrator',
      iterations: params.iterations ?? 1,
    }),
    signal: controller.signal,
  }).then(async response => {
    emitTrace('response.received', `status=${response.status}`)
    if (!response.ok) {
      let detail = ''
      try {
        detail = await response.text()
      } catch {
        detail = ''
      }
      emitTrace('response.error', `status=${response.status}${detail ? ` detail=${detail.slice(0, 500)}` : ''}`)
      throw new Error(`HTTP ${response.status}${detail ? ` - ${detail}` : ''}`)
    }
    if (!response.body) {
      emitTrace('response.body_missing')
      onError(new Error('Response body is null'))
      return
    }
    emitTrace('stream.reader_ready')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let rawChunkCount = 0
    let parsedEventCount = 0

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        emitTrace('stream.reader_done', `raw_chunks=${rawChunkCount} parsed_events=${parsedEventCount}`)
        break
      }
      rawChunkCount += 1
      if (rawChunkCount <= 3 || rawChunkCount % 25 === 0) {
        emitTrace('stream.chunk', `index=${rawChunkCount} bytes=${value?.byteLength ?? 0}`)
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            parsedEventCount += 1
            if (data.done) {
              emitTrace('stream.done_event', `index=${parsedEventCount}`)
              continue
            } else {
              onChunk({
                agent: data.agent || '',
                content: data.content || '',
                done: Boolean(data.done),
                message_type: data.message_type === 'internal' ? 'internal' : 'chat',
                groupKey: typeof data.group_key === 'string' ? data.group_key : undefined,
                isStreaming: Boolean(data.is_streaming),
                processingTarget: typeof data.processing_target === 'string' ? data.processing_target : undefined,
              })
            }
          } catch {
            emitTrace('stream.parse_error', line.slice(0, 200))
          }
        }
      }
    }
    emitTrace('stream.complete')
    onDone()
  }).catch(err => {
    if (err.name !== 'AbortError') {
      emitTrace('request.error', err instanceof Error ? err.message : String(err))
      onError(err)
    } else {
      emitTrace('request.aborted')
    }
  })

  return () => {
    emitTrace('request.abort_called')
    controller.abort()
  }
}
