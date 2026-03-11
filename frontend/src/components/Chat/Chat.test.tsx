import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Chat from './Chat'
import type { Agent } from '../../types'

const makeAgent = (id: string, name: string, isOrch = false): Agent => ({
  id,
  name,
  model: 'gpt-4o',
  is_orchestrator: isOrch,
  created_at: new Date().toISOString(),
})

describe('Chat', () => {
  const defaultProps = {
    conversation: null,
    ephemeral: {},
    streaming: false,
    agents: [],
    slaveAgents: [],
    orchestrator: undefined,
    onSend: vi.fn(),
    onNewConversation: vi.fn(),
  }

  it('renders_empty_chat', () => {
    render(<Chat {...defaultProps} />)
    expect(screen.getByText('Multi-Agent RAG')).toBeDefined()
  })

  it('mode_toggle_switches', () => {
    const conv = {
      id: '1',
      title: 'Test',
      agent_ids: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [],
    }
    render(
      <Chat
        {...defaultProps}
        conversation={conv}
        orchestrator={makeAgent('1', 'Orch', true)}
      />
    )
    const slaveButton = screen.getByText('Slave Agents')
    fireEvent.click(slaveButton)
    // After clicking, Slave Agents button should be active (green bg)
    expect(slaveButton.className).toContain('emerald')
  })

  it('message_appears_after_send', () => {
    const conv = {
      id: '1',
      title: 'Test',
      agent_ids: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [
        {
          id: 'm1',
          conversation_id: '1',
          role: 'user' as const,
          content: 'Hello world',
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
})
