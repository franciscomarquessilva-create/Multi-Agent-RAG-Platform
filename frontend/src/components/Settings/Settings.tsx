import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, Pencil, Save, Trash2, X } from 'lucide-react'
import type { AppSettings, ModelOption, PromptConfigItem } from '../../types'
import { addSettingsModel, deleteSettingsModel, updateAppSettings, updatePromptConfig, updateSettingsModel } from '../../services/api'

interface Props {
  settings: AppSettings | null
  promptConfigs: PromptConfigItem[]
  onBack: () => void
  onSettingsChanged: (settings: AppSettings) => void
  onPromptsChanged: (configs: PromptConfigItem[]) => void
}

const formatKey = (key: string) =>
  key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

export default function Settings({ settings, promptConfigs, onBack, onSettingsChanged, onPromptsChanged }: Props) {
  const [selected, setSelected] = useState<string[]>(settings?.allowed_models ?? [])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [catalogSaving, setCatalogSaving] = useState(false)

  const [newModelProvider, setNewModelProvider] = useState('OpenAI')
  const [newModelLabel, setNewModelLabel] = useState('')
  const [newModelId, setNewModelId] = useState('')

  const [editingModel, setEditingModel] = useState<string | null>(null)
  const [editProvider, setEditProvider] = useState('')
  const [editLabel, setEditLabel] = useState('')
  const [editModelId, setEditModelId] = useState('')

  // Prompt config state
  const [promptDraft, setPromptDraft] = useState<Record<string, string>>({})
  const [savingPrompts, setSavingPrompts] = useState(false)
  const [promptError, setPromptError] = useState<string | null>(null)
  const [promptSuccess, setPromptSuccess] = useState(false)

  const grouped = useMemo(() => {
    const groups = new Map<string, ModelOption[]>()
    for (const option of settings?.available_models ?? []) {
      const existing = groups.get(option.provider) ?? []
      existing.push(option)
      groups.set(option.provider, existing)
    }
    return Array.from(groups.entries())
  }, [settings])

  useEffect(() => {
    setSelected(settings?.allowed_models ?? [])
  }, [settings])

  useEffect(() => {
    const draft: Record<string, string> = {}
    for (const p of promptConfigs) {
      draft[p.key] = p.value
    }
    setPromptDraft(draft)
  }, [promptConfigs])

  const toggleModel = (model: string) => {
    setSelected(prev => prev.includes(model) ? prev.filter(item => item !== model) : [...prev, model])
  }

  const startEditModel = (option: ModelOption) => {
    setEditingModel(option.model)
    setEditProvider(option.provider)
    setEditLabel(option.label)
    setEditModelId(option.model)
    setCatalogError(null)
  }

  const cancelEditModel = () => {
    setEditingModel(null)
    setEditProvider('')
    setEditLabel('')
    setEditModelId('')
  }

  const handleAddModel = async () => {
    setCatalogSaving(true)
    setCatalogError(null)
    try {
      const updated = await addSettingsModel({
        provider: newModelProvider,
        label: newModelLabel,
        model: newModelId,
      })
      onSettingsChanged(updated)
      setSelected(updated.allowed_models)
      setNewModelLabel('')
      setNewModelId('')
    } catch (err: unknown) {
      setCatalogError(err instanceof Error ? err.message : 'Failed to add model')
    } finally {
      setCatalogSaving(false)
    }
  }

  const handleUpdateModel = async () => {
    if (!editingModel) return
    setCatalogSaving(true)
    setCatalogError(null)
    try {
      const updated = await updateSettingsModel({
        current_model: editingModel,
        provider: editProvider,
        label: editLabel,
        model: editModelId,
      })
      onSettingsChanged(updated)
      setSelected(updated.allowed_models)
      cancelEditModel()
    } catch (err: unknown) {
      setCatalogError(err instanceof Error ? err.message : 'Failed to update model')
    } finally {
      setCatalogSaving(false)
    }
  }

  const handleDeleteModel = async (model: string) => {
    setCatalogSaving(true)
    setCatalogError(null)
    try {
      const updated = await deleteSettingsModel(model)
      onSettingsChanged(updated)
      setSelected(updated.allowed_models)
      if (editingModel === model) {
        cancelEditModel()
      }
    } catch (err: unknown) {
      setCatalogError(err instanceof Error ? err.message : 'Failed to delete model')
    } finally {
      setCatalogSaving(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const updated = await updateAppSettings(selected)
      setSelected(updated.allowed_models)
      onSettingsChanged(updated)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSavePrompts = async () => {
    setSavingPrompts(true)
    setPromptError(null)
    setPromptSuccess(false)
    try {
      const updated: PromptConfigItem[] = []
      for (const [key, value] of Object.entries(promptDraft)) {
        const saved = await updatePromptConfig(key, value)
        updated.push(saved)
      }
      onPromptsChanged(updated)
      setPromptSuccess(true)
      setTimeout(() => setPromptSuccess(false), 3000)
    } catch (err: unknown) {
      setPromptError(err instanceof Error ? err.message : 'Failed to save prompts')
    } finally {
      setSavingPrompts(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-900">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-700">
        <button onClick={onBack} className="p-1 rounded hover:bg-gray-700 transition-colors">
          <ChevronLeft size={20} />
        </button>
        <h2 className="text-lg font-semibold">Settings</h2>
        <button
          onClick={handleSave}
          disabled={saving || selected.length === 0}
          className="ml-auto flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm disabled:opacity-50"
        >
          <Save size={14} />
          Save
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="rounded-xl border border-gray-700 bg-gray-800 p-4">
          <h3 className="text-sm font-semibold text-gray-200">Model Catalog</h3>
          <p className="text-sm text-gray-400 mt-1">
            Add, edit, or remove model definitions. After that, enable the models below for agent usage.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mt-4">
            <input
              value={newModelProvider}
              onChange={e => setNewModelProvider(e.target.value)}
              placeholder="Provider (e.g. OpenAI)"
              className="input-field"
            />
            <input
              value={newModelLabel}
              onChange={e => setNewModelLabel(e.target.value)}
              placeholder="Label (e.g. GPT-4.1 Mini)"
              className="input-field"
            />
            <input
              value={newModelId}
              onChange={e => setNewModelId(e.target.value)}
              placeholder="Model ID (e.g. openai/gpt-4.1-mini)"
              className="input-field"
            />
            <button
              onClick={handleAddModel}
              disabled={catalogSaving || !newModelProvider.trim() || !newModelLabel.trim() || !newModelId.trim()}
              className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm disabled:opacity-50"
            >
              Add Model
            </button>
          </div>

          {catalogError && (
            <div className="p-3 rounded-lg border border-red-700 bg-red-900/40 text-sm text-red-200 mt-3">
              {catalogError}
            </div>
          )}

          <div className="space-y-2 mt-4">
            {(settings?.available_models ?? []).map(option => (
              <div key={option.model} className="rounded-lg border border-gray-700 bg-gray-900/40 p-3">
                {editingModel === option.model ? (
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                    <input value={editProvider} onChange={e => setEditProvider(e.target.value)} className="input-field" />
                    <input value={editLabel} onChange={e => setEditLabel(e.target.value)} className="input-field" />
                    <input value={editModelId} onChange={e => setEditModelId(e.target.value)} className="input-field" />
                    <div className="flex gap-2">
                      <button
                        onClick={handleUpdateModel}
                        disabled={catalogSaving || !editProvider.trim() || !editLabel.trim() || !editModelId.trim()}
                        className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-xs disabled:opacity-50"
                      >
                        Save
                      </button>
                      <button
                        onClick={cancelEditModel}
                        className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-100">{option.label}</p>
                      <p className="text-xs text-gray-400">{option.provider}</p>
                      <p className="text-xs text-gray-500 font-mono break-all">{option.model}</p>
                    </div>
                    <button
                      onClick={() => startEditModel(option)}
                      className="p-2 rounded hover:bg-gray-700 text-gray-300"
                      title="Edit model"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => handleDeleteModel(option.model)}
                      disabled={catalogSaving}
                      className="p-2 rounded hover:bg-red-900/30 text-red-300 disabled:opacity-50"
                      title="Delete model"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-200">Allowed Models</h3>
          <p className="text-sm text-gray-400 mt-1">
            Select which catalog models are enabled for agent usage.
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-lg border border-red-700 bg-red-900/40 text-sm text-red-200">
            {error}
          </div>
        )}

        {!settings && (
          <p className="text-sm text-gray-500">Loading settings...</p>
        )}

        {grouped.map(([provider, options]) => (
          <section key={provider} className="rounded-xl border border-gray-700 bg-gray-800 p-4">
            <h4 className="text-sm font-semibold text-gray-200 mb-3">{provider}</h4>
            <div className="space-y-2">
              {options.map(option => (
                <label key={option.model} className="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selected.includes(option.model)}
                    onChange={() => toggleModel(option.model)}
                    className="accent-blue-500 mt-1"
                  />
                  <div>
                    <div className="text-sm text-gray-100">{option.label}</div>
                    <div className="text-xs text-gray-500">{option.model}</div>
                  </div>
                </label>
              ))}
            </div>
          </section>
        ))}

        {/* Prompt Configuration */}
        <div className="pt-4 border-t border-gray-700">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold text-gray-200">Prompt Configuration</h3>
            <button
              onClick={handleSavePrompts}
              disabled={savingPrompts || promptConfigs.length === 0}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm disabled:opacity-50"
            >
              <Save size={14} />
              {savingPrompts ? 'Saving…' : 'Save Prompts'}
            </button>
          </div>
          <p className="text-sm text-gray-400 mb-4">
            Configure the system prompts used by broadcast and orchestrate orchestrators.
            Changes take effect immediately for new messages.
          </p>

          {promptError && (
            <div className="p-3 rounded-lg border border-red-700 bg-red-900/40 text-sm text-red-200 mb-4">
              {promptError}
            </div>
          )}

          {promptSuccess && (
            <div className="p-3 rounded-lg border border-green-700 bg-green-900/40 text-sm text-green-200 mb-4">
              Prompts saved successfully.
            </div>
          )}

          {promptConfigs.length === 0 && (
            <p className="text-sm text-gray-500">Loading prompts...</p>
          )}

          <div className="space-y-5">
            {promptConfigs.map(p => (
              <div key={p.key} className="rounded-xl border border-gray-700 bg-gray-800 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-gray-200">{formatKey(p.key)}</span>
                  <span className="text-[10px] font-mono text-gray-500">{p.key}</span>
                </div>
                {p.description && (
                  <p className="text-xs text-gray-400">{p.description}</p>
                )}
                <textarea
                  value={promptDraft[p.key] ?? p.value}
                  onChange={e => setPromptDraft(prev => ({ ...prev, [p.key]: e.target.value }))}
                  className="input-field w-full min-h-[80px] text-xs font-mono resize-y"
                  spellCheck={false}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
