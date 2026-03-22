import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import Chat from './Chat'
import type { Agent } from '../../types'

const makeAgent = (id: string, name: string, isOrch = false): Agent => ({
  id,
  name,
  model: 'gpt-4o',
  agent_type: isOrch ? 'orchestrator' : 'slave',
  purpose: '',
  instructions: '',
  orchestrator_mode: isOrch ? 'orchestrate' : null,
  allowed_slave_ids: [],
  is_orchestrator: isOrch,
  use_default_key: false,
  created_at: new Date().toISOString(),
})

describe('Chat', () => {
  const defaultProps = {
    conversation: null,
    ephemeral: {},
    streaming: false,
    agents: [],
    slaveAgents: [],
    onSend: vi.fn(),
    onNewConversation: vi.fn(),
  }

  it('renders_empty_chat', () => {
    render(<Chat {...defaultProps} />)
    expect(screen.getByText('Multi-Agent RAG')).toBeDefined()
  })

  it('shows_orchestrator_instruction_target_label', () => {
    const conv = {
      id: '1',
      title: 'Test',
      orchestrator_id: '1',
      agent_ids: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [],
    }
    render(
      <Chat
        {...defaultProps}
        conversation={conv}
        agents={[makeAgent('1', 'Orch', true)]}
      />
    )
    expect(screen.queryByText('Instruction target: Orchestrator')).toBeNull()
  })

  it('message_appears_after_send', () => {
    const conv = {
      id: '1',
      title: 'Test',
      orchestrator_id: '1',
      agent_ids: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [
        {
          id: 'm1',
          conversation_id: '1',
          role: 'user' as const,
          content: 'Hello world',
          message_type: 'chat' as const,
          mode: 'orchestrator' as const,
          agent_id: null,
          agent_name: null,
          created_at: new Date().toISOString(),
        }
      ],
    }
    render(<Chat {...defaultProps} conversation={conv} />)
    expect(screen.getByText('Hello world')).toBeDefined()
  })

  it('internal_messages_render_in_collapsed_boxes', () => {
    const conv = {
      id: '1',
      title: 'Internal Test',
      orchestrator_id: '1',
      agent_ids: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [
        {
          id: 'm1',
          conversation_id: '1',
          role: 'assistant' as const,
          content: 'Please investigate the data inconsistency.',
          message_type: 'internal' as const,
          mode: 'orchestrator' as const,
          agent_id: null,
          agent_name: 'Lead -> Researcher · Round 1',
          created_at: new Date().toISOString(),
        },
      ],
    }

    const { container } = render(<Chat {...defaultProps} conversation={conv} />)
    expect(screen.getByText('Lead -> Researcher · Round 1')).toBeDefined()
    expect(container.querySelector('details:not([open])')).not.toBeNull()
  })
})
