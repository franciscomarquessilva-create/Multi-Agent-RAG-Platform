import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Sidebar from './Sidebar'
import type { Conversation } from '../../types'

const makeConv = (id: string, title: string): Conversation => ({
  id,
  title,
  orchestrator_id: 'orch-1',
  agent_ids: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
})

describe('Sidebar', () => {
  const defaultProps = {
    conversations: [],
    currentUser: null,
    impersonatingUserEmail: null,
    onStopImpersonating: vi.fn(),
    onSelectConversation: vi.fn(),
    onNewConversation: vi.fn(),
    onDeleteConversation: vi.fn(),
    onManageAgents: vi.fn(),
    onOpenSettings: vi.fn(),
    onOpenAudit: vi.fn(),
  }

  it('renders_conversations', () => {
    render(
      <Sidebar
        {...defaultProps}
        conversations={[makeConv('1', 'First Chat'), makeConv('2', 'Second Chat')]}
      />
    )
    expect(screen.getByText('First Chat')).toBeDefined()
    expect(screen.getByText('Second Chat')).toBeDefined()
  })

  it('click_conversation_selects', () => {
    const onSelect = vi.fn()
    const conv = makeConv('1', 'My Conversation')
    render(
      <Sidebar
        {...defaultProps}
        conversations={[conv]}
        onSelectConversation={onSelect}
      />
    )
    fireEvent.click(screen.getByText('My Conversation'))
    expect(onSelect).toHaveBeenCalledWith(conv)
  })

  it('new_chat_button_fires_callback', () => {
    const onCreate = vi.fn()
    render(<Sidebar {...defaultProps} onNewConversation={onCreate} />)
    fireEvent.click(screen.getByText('New Chat'))
    expect(onCreate).toHaveBeenCalled()
  })
})
