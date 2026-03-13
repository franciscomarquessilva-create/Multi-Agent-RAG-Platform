import { useState } from 'react'
import { X, Users } from 'lucide-react'
import type { Agent } from '../types'

interface Props {
  agents: Agent[]
  onConfirm: (orchestratorId: string, agentIds: string[]) => void
  onCancel: () => void
}

export default function NewConversationModal({ agents, onConfirm, onCancel }: Props) {
  const orchestrators = agents.filter(a => a.agent_type === 'orchestrator')
  const slaveAgents = agents.filter(a => a.agent_type === 'slave')
  const [selectedOrchestratorId, setSelectedOrchestratorId] = useState<string>(orchestrators[0]?.id || '')

  const defaultSlaveSelection = selectedOrchestratorId
    ? (agents.find(a => a.id === selectedOrchestratorId)?.allowed_slave_ids || [])
    : []
  const [selectedIds, setSelectedIds] = useState<string[]>(defaultSlaveSelection)

  const handleOrchestratorChange = (orchId: string) => {
    setSelectedOrchestratorId(orchId)
    const defaults = agents.find(a => a.id === orchId)?.allowed_slave_ids || []
    setSelectedIds(defaults)
  }

  const toggle = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-md">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-blue-400" />
            <h3 className="font-semibold">New Conversation</h3>
          </div>
          <button onClick={onCancel} className="p-1 rounded hover:bg-gray-700 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-4">
          <p className="text-sm text-gray-400 mb-2">Choose orchestrator:</p>
          {orchestrators.length === 0 ? (
            <p className="text-sm text-red-400 mb-4">No orchestrator configured. Create one in Manage Agents.</p>
          ) : (
            <select
              value={selectedOrchestratorId}
              onChange={e => handleOrchestratorChange(e.target.value)}
              className="input-field w-full mb-4"
            >
              {orchestrators.map(orch => (
                <option key={orch.id} value={orch.id}>
                  {orch.name} ({orch.orchestrator_mode})
                </option>
              ))}
            </select>
          )}

          <p className="text-sm text-gray-400 mb-3">Select slave agents to participate in this conversation:</p>

          {slaveAgents.length === 0 ? (
            <p className="text-sm text-gray-500 italic">No slave agents available. Only the orchestrator will participate.</p>
          ) : (
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {slaveAgents.map(agent => (
                <label key={agent.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(agent.id)}
                    onChange={() => toggle(agent.id)}
                    className="accent-blue-500 w-4 h-4"
                  />
                  <div>
                    <span className="text-sm font-medium text-gray-200">{agent.name}</span>
                    <span className="text-xs text-gray-500 ml-2">{agent.model}</span>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="flex gap-2 p-4 border-t border-gray-700">
          <button
            onClick={() => onConfirm(selectedOrchestratorId, selectedIds)}
            disabled={!selectedOrchestratorId}
            className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
          >
            Start Conversation
          </button>
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
