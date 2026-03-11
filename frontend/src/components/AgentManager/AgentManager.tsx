import React, { useState } from 'react'
import { Plus, Trash2, Crown, ChevronLeft, Edit2, Check, X } from 'lucide-react'
import type { Agent, AgentCreate, AgentUpdate } from '../../types'
import { createAgent, updateAgent, deleteAgent, setOrchestrator } from '../../services/api'

interface Props {
  agents: Agent[]
  onAgentsChanged: () => void
  onBack: () => void
}

interface AgentFormData {
  name: string
  model: string
  api_key: string
}

const defaultForm: AgentFormData = { name: '', model: 'gpt-4o', api_key: '' }

export default function AgentManager({ agents, onAgentsChanged, onBack }: Props) {
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<AgentFormData>(defaultForm)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<AgentFormData>(defaultForm)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name || !form.model || !form.api_key) {
      setError('All fields are required')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await createAgent(form as AgentCreate)
      setForm(defaultForm)
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
    setLoading(true)
    setError(null)
    try {
      const update: AgentUpdate = {}
      if (editForm.name) update.name = editForm.name
      if (editForm.model) update.model = editForm.model
      if (editForm.api_key) update.api_key = editForm.api_key
      await updateAgent(id, update)
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

  const handleSetOrchestrator = async (id: string) => {
    setLoading(true)
    setError(null)
    try {
      await setOrchestrator(id)
      onAgentsChanged()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to set orchestrator'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const startEdit = (agent: Agent) => {
    setEditingId(agent.id)
    setEditForm({ name: agent.name, model: agent.model, api_key: '' })
  }

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-700">
        <button
          onClick={onBack}
          className="p-1 rounded hover:bg-gray-700 transition-colors"
        >
          <ChevronLeft size={20} />
        </button>
        <h2 className="text-lg font-semibold">Manage Agents</h2>
        <button
          onClick={() => { setShowForm(true); setError(null) }}
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

        {/* Create form */}
        {showForm && (
          <form onSubmit={handleCreate} className="mb-6 p-4 bg-gray-800 rounded-xl border border-gray-700">
            <h3 className="text-sm font-semibold mb-3 text-gray-300">New Agent</h3>
            <div className="grid grid-cols-1 gap-3">
              <input
                type="text"
                placeholder="Agent name"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="input-field"
              />
              <input
                type="text"
                placeholder="Model (e.g. gpt-4o, claude-3-5-sonnet)"
                value={form.model}
                onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
                className="input-field"
              />
              <input
                type="password"
                placeholder="API Key"
                value={form.api_key}
                onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))}
                className="input-field"
              />
            </div>
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
                onClick={() => { setShowForm(false); setForm(defaultForm) }}
                className="px-4 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Agents list */}
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
                agent.is_orchestrator
                  ? 'border-blue-600 bg-blue-900/20'
                  : 'border-gray-700 bg-gray-800'
              }`}
            >
              {editingId === agent.id ? (
                <div className="space-y-2">
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Name"
                    className="input-field w-full"
                  />
                  <input
                    type="text"
                    value={editForm.model}
                    onChange={e => setEditForm(f => ({ ...f, model: e.target.value }))}
                    placeholder="Model"
                    className="input-field w-full"
                  />
                  <input
                    type="password"
                    value={editForm.api_key}
                    onChange={e => setEditForm(f => ({ ...f, api_key: e.target.value }))}
                    placeholder="New API key (leave blank to keep)"
                    className="input-field w-full"
                  />
                  <div className="flex gap-2 mt-2">
                    <button onClick={() => handleUpdate(agent.id)} disabled={loading} className="p-1.5 bg-emerald-600 hover:bg-emerald-700 rounded transition-colors">
                      <Check size={14} />
                    </button>
                    <button onClick={() => setEditingId(null)} className="p-1.5 bg-gray-600 hover:bg-gray-500 rounded transition-colors">
                      <X size={14} />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-200">{agent.name}</span>
                      {agent.is_orchestrator && (
                        <span className="flex items-center gap-1 text-xs bg-blue-700 text-blue-100 px-2 py-0.5 rounded-full">
                          <Crown size={10} />
                          Orchestrator
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{agent.model}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    {!agent.is_orchestrator && (
                      <button
                        onClick={() => handleSetOrchestrator(agent.id)}
                        disabled={loading}
                        title="Set as orchestrator"
                        className="p-1.5 rounded hover:bg-yellow-700/40 text-yellow-400 transition-colors"
                      >
                        <Crown size={14} />
                      </button>
                    )}
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
