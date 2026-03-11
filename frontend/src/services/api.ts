import axios from 'axios'
import type { Agent, AgentCreate, AgentUpdate, Conversation, ConversationWithMessages } from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE_URL })

// Agents
export const getAgents = () => api.get<Agent[]>('/agents').then(r => r.data)
export const createAgent = (data: AgentCreate) => api.post<Agent>('/agents', data).then(r => r.data)
export const updateAgent = (id: string, data: AgentUpdate) => api.put<Agent>(`/agents/${id}`, data).then(r => r.data)
export const deleteAgent = (id: string) => api.delete(`/agents/${id}`)
export const setOrchestrator = (id: string) => api.patch<Agent>(`/agents/${id}/orchestrator`).then(r => r.data)

// Conversations
export const getConversations = () => api.get<Conversation[]>('/conversations').then(r => r.data)
export const createConversation = (title: string, agentIds: string[]) =>
  api.post<Conversation>('/conversations', { title, agent_ids: agentIds }).then(r => r.data)
export const getConversation = (id: string) =>
  api.get<ConversationWithMessages>(`/conversations/${id}`).then(r => r.data)
export const deleteConversation = (id: string) => api.delete(`/conversations/${id}`)

// Chat streaming
export interface SendMessageParams {
  conversationId: string
  content: string
  mode: 'orchestrator' | 'slave'
  agentIds?: string[]
}

export const sendMessageStream = (
  params: SendMessageParams,
  onChunk: (agent: string, content: string) => void,
  onDone: () => void,
  onError: (err: Error) => void
): (() => void) => {
  const controller = new AbortController()

  fetch(`${BASE_URL}/chat/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversation_id: params.conversationId,
      content: params.content,
      mode: params.mode,
      agent_ids: params.agentIds,
    }),
    signal: controller.signal,
  }).then(async response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    if (!response.body) {
      onError(new Error('Response body is null'))
      return
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.done) {
              onDone()
            } else {
              onChunk(data.agent || '', data.content || '')
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    }
    onDone()
  }).catch(err => {
    if (err.name !== 'AbortError') {
      onError(err)
    }
  })

  return () => controller.abort()
}
