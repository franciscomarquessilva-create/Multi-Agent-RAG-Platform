import React, { useEffect, useMemo, useState } from 'react'
import { Plus, Trash2, Crown, ChevronLeft, Edit2, Check, X } from 'lucide-react'
import type { Agent, AgentCreate, AgentUpdate, OrchestrationRule, PromptConfigItem } from '../../types'
import { createAgent, updateAgent, deleteAgent } from '../../services/api'

interface Props {
  agents: Agent[]
  allowedModels: string[]
  promptConfigs: PromptConfigItem[]
  onAgentsChanged: () => void
  onBack: () => void
}

interface AgentFormData {
  name: string
  model: string
  api_key: string
  agent_type: 'orchestrator' | 'slave'
  purpose: string
  instructions: string
  orchestrator_mode: 'broadcast' | 'orchestrate'
  allowed_slave_ids: string[]
  orchestration_rules: OrchestrationRule[]
}

const makeDefaultForm = (defaultModel = ''): AgentFormData => ({
  name: '',
  model: defaultModel,
  api_key: '',
  agent_type: 'slave',
  purpose: '',
  instructions: '',
  orchestrator_mode: 'orchestrate',
  allowed_slave_ids: [],
  orchestration_rules: [],
})

function RuleEditor({
  rules,
  allowedSlaveIds,
  slaveAgents,
  onChange,
}: {
  rules: OrchestrationRule[]
  allowedSlaveIds: string[]
  slaveAgents: Agent[]
  onChange: (rules: OrchestrationRule[]) => void
}) {
  const allowedSlaves = slaveAgents.filter(a => allowedSlaveIds.includes(a.id))

  const addRule = () => {
    if (allowedSlaves.length === 0) return
    onChange([
      ...rules,
      { slave_agent_id: allowedSlaves[0].id, rule: '' },
    ])
  }

  const removeRule = (index: number) => {
    onChange(rules.filter((_, i) => i !== index))
  }

  const updateRule = (index: number, next: OrchestrationRule) => {
    onChange(rules.map((r, i) => (i === index ? next : r)))
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">Routing rules</span>
        <button
          type="button"
          onClick={addRule}
          className="text-xs px-2 py-1 rounded bg-gray-700 hover:bg-gray-600"
          disabled={allowedSlaves.length === 0}
        >
          Add Rule
        </button>
      </div>

      {rules.length === 0 && (
        <p className="text-xs text-gray-500">No rules defined. The orchestrator will use selected slave agents directly.</p>
      )}

      {rules.map((rule, index) => (
        <div key={`${rule.slave_agent_id}-${index}`} className="grid grid-cols-12 gap-2 items-center">
          <select
            value={rule.slave_agent_id}
            onChange={e => updateRule(index, { ...rule, slave_agent_id: e.target.value })}
            className="col-span-4 input-field"
          >
            {allowedSlaves.map(slave => (
              <option key={slave.id} value={slave.id}>{slave.name}</option>
            ))}
          </select>
          <input
            value={rule.rule}
            onChange={e => updateRule(index, { ...rule, rule: e.target.value })}
            placeholder="When to contact this agent (keywords or condition)"
            className="col-span-7 input-field"
          />
          <button
            type="button"
            onClick={() => removeRule(index)}
            className="col-span-1 p-2 rounded hover:bg-red-900/40 text-red-400"
            title="Remove rule"
          >
            <Trash2 size={13} />
          </button>
        </div>
      ))}
    </div>
  )
}

export default function AgentManager({ agents, allowedModels, promptConfigs, onAgentsChanged, onBack }: Props) {
  const defaultModel = allowedModels[0] ?? ''
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<AgentFormData>(makeDefaultForm(defaultModel))
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<AgentFormData>(makeDefaultForm(defaultModel))
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const getDefaultPrompt = (key: string): string =>
    promptConfigs.find(p => p.key === key)?.value ?? ''

  const applyOrchestratorDefaults = (data: AgentFormData, mode: 'broadcast' | 'orchestrate'): AgentFormData => ({
    ...data,
    orchestrator_mode: mode,
    purpose: getDefaultPrompt(`${mode}_default_purpose`),
    instructions: getDefaultPrompt(`${mode}_default_instructions`),
  })

  useEffect(() => {
    if (allowedModels.length === 0) {
      return
    }
    setForm(prev => prev.model ? prev : { ...prev, model: allowedModels[0] })
    setEditForm(prev => prev.model ? prev : { ...prev, model: allowedModels[0] })
  }, [allowedModels])

  const slaveAgents = useMemo(() => agents.filter(a => a.agent_type === 'slave'), [agents])

  const toCreatePayload = (data: AgentFormData): AgentCreate => ({
    name: data.name,
    model: data.model,
    api_key: data.api_key,
    agent_type: data.agent_type,
    purpose: data.purpose,
    instructions: data.instructions,
    orchestrator_mode: data.agent_type === 'orchestrator' ? data.orchestrator_mode : undefined,
    allowed_slave_ids: data.agent_type === 'orchestrator' ? data.allowed_slave_ids : [],
    orchestration_rules: data.agent_type === 'orchestrator' ? data.orchestration_rules : [],
  })

  const toUpdatePayload = (data: AgentFormData): AgentUpdate => ({
    name: data.name,
    model: data.model,
    api_key: data.api_key || undefined,
    agent_type: data.agent_type,
    purpose: data.purpose,
    instructions: data.instructions,
    orchestrator_mode: data.agent_type === 'orchestrator' ? data.orchestrator_mode : undefined,
    allowed_slave_ids: data.agent_type === 'orchestrator' ? data.allowed_slave_ids : [],
    orchestration_rules: data.agent_type === 'orchestrator' ? data.orchestration_rules : [],
  })

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (allowedModels.length === 0) {
      setError('Enable at least one model in Settings before creating agents')
      return
    }
    if (!form.name || !form.model || !form.api_key) {
      setError('Name, model and API key are required')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await createAgent(toCreatePayload(form))
      setForm(makeDefaultForm(defaultModel))
      setShowForm(false)
      onAgentsChanged()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create agent'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdate = async (id: string) => {
    if (allowedModels.length === 0) {
      setError('Enable at least one model in Settings before updating agents')
      return
    }
    if (!editForm.name || !editForm.model) {
      setError('Name and model are required')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await updateAgent(id, toUpdatePayload(editForm))
      setEditingId(null)
      onAgentsChanged()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update agent'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this agent?')) return
    setLoading(true)
    setError(null)
    try {
      await deleteAgent(id)
      onAgentsChanged()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete agent'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const startEdit = (agent: Agent) => {
    setEditingId(agent.id)
    setEditForm({
      name: agent.name,
      model: agent.model,
      api_key: '',
      agent_type: agent.agent_type,
      purpose: agent.purpose || '',
      instructions: agent.instructions || '',
      orchestrator_mode: agent.orchestrator_mode || 'orchestrate',
      allowed_slave_ids: agent.allowed_slave_ids || [],
      orchestration_rules: agent.orchestration_rules || [],
    })
  }

  const getModelOptions = (currentModel: string) => (
    currentModel && !allowedModels.includes(currentModel)
      ? [currentModel, ...allowedModels]
      : allowedModels
  )

  const renderAgentForm = (
    data: AgentFormData,
    onChange: (next: AgentFormData) => void,
    withPasswordHint = false,
  ) => (
    <>
      <div className="grid grid-cols-1 gap-3">
        <input
          type="text"
          placeholder="Agent name"
          value={data.name}
          onChange={e => onChange({ ...data, name: e.target.value })}
          className="input-field"
        />
        <select
          value={data.model}
          onChange={e => onChange({ ...data, model: e.target.value })}
          className="input-field"
          disabled={allowedModels.length === 0}
        >
          {getModelOptions(data.model).length === 0 ? (
            <option value="">No enabled models. Configure Settings first.</option>
          ) : (
            getModelOptions(data.model).map(model => (
              <option key={model} value={model}>{model}</option>
            ))
          )}
        </select>
        <select
          value={data.agent_type}
          onChange={e => {
            const type = e.target.value as 'orchestrator' | 'slave'
            if (type === 'orchestrator') {
              onChange(applyOrchestratorDefaults({ ...data, agent_type: type }, data.orchestrator_mode))
            } else {
              onChange({ ...data, agent_type: type })
            }
          }}
          className="input-field"
        >
          <option value="slave">Slave</option>
          <option value="orchestrator">Orchestrator</option>
        </select>
        <textarea
          placeholder="Purpose: what this agent is responsible for"
          value={data.purpose}
          onChange={e => onChange({ ...data, purpose: e.target.value })}
          className="input-field min-h-20"
        />
        <textarea
          placeholder="Behavior instructions: how this agent should act"
          value={data.instructions}
          onChange={e => onChange({ ...data, instructions: e.target.value })}
          className="input-field min-h-20"
        />
        <input
          type="password"
          placeholder={withPasswordHint ? 'New API key (leave blank to keep)' : 'API Key'}
          value={data.api_key}
          onChange={e => onChange({ ...data, api_key: e.target.value })}
          className="input-field"
        />
      </div>

      {data.agent_type === 'orchestrator' && (
        <div className="mt-3 space-y-3 p-3 rounded-lg border border-gray-700 bg-gray-900/40">
          <select
            value={data.orchestrator_mode}
            onChange={e => onChange(applyOrchestratorDefaults(data, e.target.value as 'broadcast' | 'orchestrate'))}
            className="input-field"
          >
            <option value="broadcast">broadcast</option>
            <option value="orchestrate">orchestrate</option>
          </select>

          <div>
            <p className="text-xs text-gray-400 mb-2">Allowed slave agents</p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {slaveAgents.length === 0 && <p className="text-xs text-gray-500">No slave agents available</p>}
              {slaveAgents.map(slave => (
                <label key={slave.id} className="flex items-center gap-2 text-sm text-gray-200">
                  <input
                    type="checkbox"
                    checked={data.allowed_slave_ids.includes(slave.id)}
                    onChange={() => {
                      const exists = data.allowed_slave_ids.includes(slave.id)
                      const nextAllowed = exists
                        ? data.allowed_slave_ids.filter(id => id !== slave.id)
                        : [...data.allowed_slave_ids, slave.id]
                      const nextRules = data.orchestration_rules.filter(r => nextAllowed.includes(r.slave_agent_id))
                      onChange({ ...data, allowed_slave_ids: nextAllowed, orchestration_rules: nextRules })
                    }}
                  />
                  <span>{slave.name}</span>
                </label>
              ))}
            </div>
          </div>

          <RuleEditor
            rules={data.orchestration_rules}
            allowedSlaveIds={data.allowed_slave_ids}
            slaveAgents={slaveAgents}
            onChange={rules => onChange({ ...data, orchestration_rules: rules })}
          />
        </div>
      )}
    </>
  )

  return (
    <div className="flex flex-col h-full bg-gray-900">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-700">
        <button onClick={onBack} className="p-1 rounded hover:bg-gray-700 transition-colors">
          <ChevronLeft size={20} />
        </button>
        <h2 className="text-lg font-semibold">Manage Agents</h2>
        <button
          onClick={() => {
            setShowForm(true)
            setError(null)
          }}
          className="ml-auto flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm transition-colors"
        >
          <Plus size={16} />
          Add Agent
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-sm text-red-300">
            {error}
          </div>
        )}

        {showForm && (
          <form onSubmit={handleCreate} className="mb-6 p-4 bg-gray-800 rounded-xl border border-gray-700">
            <h3 className="text-sm font-semibold mb-3 text-gray-300">New Agent</h3>
            {renderAgentForm(form, setForm)}
            <div className="flex gap-2 mt-3">
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm disabled:opacity-50 transition-colors"
              >
                Create
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false)
                  setForm(makeDefaultForm(defaultModel))
                }}
                className="px-4 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {agents.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <p>No agents configured. Add your first agent above.</p>
          </div>
        )}

        <div className="space-y-3">
          {agents.map(agent => (
            <div
              key={agent.id}
              className={`p-4 rounded-xl border transition-colors ${
                agent.agent_type === 'orchestrator'
                  ? 'border-blue-600 bg-blue-900/20'
                  : 'border-gray-700 bg-gray-800'
              }`}
            >
              {editingId === agent.id ? (
                <div className="space-y-2">
                  {renderAgentForm(editForm, setEditForm, true)}
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleUpdate(agent.id)}
                      disabled={loading}
                      className="p-1.5 bg-emerald-600 hover:bg-emerald-700 rounded transition-colors"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="p-1.5 bg-gray-600 hover:bg-gray-500 rounded transition-colors"
                    >
                      <X size={14} />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-200">{agent.name}</span>
                      {agent.agent_type === 'orchestrator' && (
                        <span className="flex items-center gap-1 text-xs bg-blue-700 text-blue-100 px-2 py-0.5 rounded-full">
                          <Crown size={10} />
                          Orchestrator ({agent.orchestrator_mode})
                        </span>
                      )}
                      {agent.agent_type === 'slave' && (
                        <span className="text-xs bg-emerald-700 text-emerald-100 px-2 py-0.5 rounded-full">Slave</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{agent.model}</p>
                    {agent.purpose && <p className="text-xs text-gray-500 mt-1">{agent.purpose}</p>}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => startEdit(agent)}
                      className="p-1.5 rounded hover:bg-gray-700 text-gray-400 transition-colors"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(agent.id)}
                      disabled={loading || agents.length <= 1}
                      title={agents.length <= 1 ? 'Cannot delete last agent' : 'Delete'}
                      className="p-1.5 rounded hover:bg-red-900/40 text-gray-400 hover:text-red-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
