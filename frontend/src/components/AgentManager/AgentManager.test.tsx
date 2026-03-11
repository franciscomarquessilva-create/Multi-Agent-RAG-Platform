import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import AgentManager from './AgentManager'
import type { Agent } from '../../types'

vi.mock('../../services/api', () => ({
  createAgent: vi.fn(),
  updateAgent: vi.fn(),
  deleteAgent: vi.fn(),
  setOrchestrator: vi.fn(),
}))

const makeAgent = (id: string, name: string, isOrch = false): Agent => ({
  id,
  name,
  model: 'gpt-4o',
  is_orchestrator: isOrch,
  created_at: new Date().toISOString(),
})

describe('AgentManager', () => {
  const defaultProps = {
    agents: [],
    onAgentsChanged: vi.fn(),
    onBack: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders_agent_list', () => {
    render(
      <AgentManager
        {...defaultProps}
        agents={[makeAgent('1', 'AlphaAgent', true), makeAgent('2', 'BetaAgent')]}
      />
    )
    expect(screen.getByText('AlphaAgent')).toBeDefined()
    expect(screen.getByText('BetaAgent')).toBeDefined()
  })

  it('shows_orchestrator_badge', () => {
    render(
      <AgentManager
        {...defaultProps}
        agents={[makeAgent('1', 'OrchestratorAgent', true)]}
      />
    )
    expect(screen.getByText('Orchestrator')).toBeDefined()
  })
})
