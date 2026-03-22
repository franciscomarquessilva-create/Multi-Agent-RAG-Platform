import { useEffect, useState } from 'react'
import { ChevronLeft, Key, Pencil, Save, Trash2, X } from 'lucide-react'
import type { AppSettings, ModelOption, PromptConfigItem } from '../../types'
import { addSettingsModel, deleteDefaultKey, deleteSettingsModel, setDefaultKey, updateAppSettings, updatePromptConfig, updateSettingsModel } from '../../services/api'

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
  const [creditsPerProcess, setCreditsPerProcess] = useState<number>(settings?.credits_per_process ?? 1)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [catalogSaving, setCatalogSaving] = useState(false)

  // Default provider keys state
  const [defaultKeyProvider, setDefaultKeyProvider] = useState('')
  const [defaultKeyValue, setDefaultKeyValue] = useState('')
  const [defaultKeySaving, setDefaultKeySaving] = useState(false)
  const [defaultKeyError, setDefaultKeyError] = useState<string | null>(null)

  const [newModelProvider, setNewModelProvider] = useState('OpenAI')
  const [newModelLabel, setNewModelLabel] = useState('')
  const [newModelId, setNewModelId] = useState('')
  const [newModelEnabled, setNewModelEnabled] = useState(true)

  const [editingModel, setEditingModel] = useState<string | null>(null)
  const [editProvider, setEditProvider] = useState('')
  const [editLabel, setEditLabel] = useState('')
  const [editModelId, setEditModelId] = useState('')
  const [editEnabled, setEditEnabled] = useState(true)

  // Prompt config state
  const [promptDraft, setPromptDraft] = useState<Record<string, string>>({})
  const [savingPrompts, setSavingPrompts] = useState(false)
  const [promptError, setPromptError] = useState<string | null>(null)
  const [promptSuccess, setPromptSuccess] = useState(false)

  useEffect(() => {
    setCreditsPerProcess(settings?.credits_per_process ?? 1)
  }, [settings])

  useEffect(() => {
    const draft: Record<string, string> = {}
    for (const p of promptConfigs) {
      draft[p.key] = p.value
    }
    setPromptDraft(draft)
  }, [promptConfigs])

  const startEditModel = (option: ModelOption) => {
    setEditingModel(option.model)
    setEditProvider(option.provider)
    setEditLabel(option.label)
    setEditModelId(option.model)
    setEditEnabled(option.enabled)
    setCatalogError(null)
  }

  const cancelEditModel = () => {
    setEditingModel(null)
    setEditProvider('')
    setEditLabel('')
    setEditModelId('')
    setEditEnabled(true)
  }

  const handleAddModel = async () => {
    setCatalogSaving(true)
    setCatalogError(null)
    try {
      const updated = await addSettingsModel({
        provider: newModelProvider,
        label: newModelLabel,
        model: newModelId,
        enabled: newModelEnabled,
      })
      onSettingsChanged(updated)
      setNewModelLabel('')
      setNewModelId('')
      setNewModelEnabled(true)
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
        enabled: editEnabled,
      })
      onSettingsChanged(updated)
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
      const updated = await updateAppSettings(creditsPerProcess)
      setCreditsPerProcess(updated.credits_per_process)
      onSettingsChanged(updated)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSetDefaultKey = async () => {
    if (!defaultKeyProvider.trim() || !defaultKeyValue.trim()) return
    setDefaultKeySaving(true)
    setDefaultKeyError(null)
    try {
      const updated = await setDefaultKey(defaultKeyProvider.trim(), defaultKeyValue.trim())
      onSettingsChanged(updated)
      setDefaultKeyProvider('')
      setDefaultKeyValue('')
    } catch (err: unknown) {
      setDefaultKeyError(err instanceof Error ? err.message : 'Failed to save key')
    } finally {
      setDefaultKeySaving(false)
    }
  }

  const handleDeleteDefaultKey = async (provider: string) => {
    setDefaultKeySaving(true)
    setDefaultKeyError(null)
    try {
      const updated = await deleteDefaultKey(provider)
      onSettingsChanged(updated)
    } catch (err: unknown) {
      setDefaultKeyError(err instanceof Error ? err.message : 'Failed to delete key')
    } finally {
      setDefaultKeySaving(false)
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
          disabled={saving}
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
            Add, edit, enable, or disable model definitions used by agents.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-2 mt-4">
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
            <label className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={newModelEnabled}
                onChange={e => setNewModelEnabled(e.target.checked)}
                className="accent-blue-500"
              />
              Enabled
            </label>
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
                  <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
                    <input value={editProvider} onChange={e => setEditProvider(e.target.value)} className="input-field" />
                    <input value={editLabel} onChange={e => setEditLabel(e.target.value)} className="input-field" />
                    <input value={editModelId} onChange={e => setEditModelId(e.target.value)} className="input-field" />
                    <label className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 text-sm text-gray-300">
                      <input
                        type="checkbox"
                        checked={editEnabled}
                        onChange={e => setEditEnabled(e.target.checked)}
                        className="accent-blue-500"
                      />
                      Enabled
                    </label>
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
                      <p className={`text-xs mt-1 ${option.enabled ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {option.enabled ? 'Enabled' : 'Disabled'}
                      </p>
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

        {error && (
          <div className="p-3 rounded-lg border border-red-700 bg-red-900/40 text-sm text-red-200">
            {error}
          </div>
        )}

        {!settings && (
          <p className="text-sm text-gray-500">Loading settings...</p>
        )}

        {/* Credits per Process */}
        <div className="rounded-xl border border-gray-700 bg-gray-800 p-4 space-y-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-200">Credits per Process</h3>
            <p className="text-sm text-gray-400 mt-1">
              Credits deducted from a user's balance each time an agent that uses the default key makes an LLM call.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="number"
              min={0}
              value={creditsPerProcess}
              onChange={e => setCreditsPerProcess(Math.max(0, parseInt(e.target.value, 10) || 0))}
              className="input-field w-28 text-center"
            />
            <span className="text-sm text-gray-400">credits / call</span>
          </div>
        </div>

        {/* Default LLM Keys */}
        <div className="rounded-xl border border-gray-700 bg-gray-800 p-4 space-y-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-200">Default LLM Keys</h3>
            <p className="text-sm text-gray-400 mt-1">
              Store API keys per provider. Agents configured to use the "default key" will use the provider key matching their model.
              Keys are stored encrypted.
            </p>
          </div>

          {defaultKeyError && (
            <div className="p-3 rounded-lg border border-red-700 bg-red-900/40 text-sm text-red-200">
              {defaultKeyError}
            </div>
          )}

          {/* Existing keys */}
          {(settings?.default_key_providers ?? []).length > 0 && (
            <div className="space-y-2">
              {(settings?.default_key_providers ?? []).map(provider => (
                <div key={provider} className="flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-700 bg-gray-900/40">
                  <Key size={14} className="text-green-400 shrink-0" />
                  <span className="flex-1 text-sm font-mono text-gray-200 truncate">{provider}</span>
                  <span className="text-xs text-gray-500">key stored</span>
                  <button
                    onClick={() => handleDeleteDefaultKey(provider)}
                    disabled={defaultKeySaving}
                    className="p-1 rounded hover:bg-red-900/30 text-red-400 disabled:opacity-50"
                    title="Remove key"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add new key */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <select
              value={defaultKeyProvider}
              onChange={e => setDefaultKeyProvider(e.target.value)}
              className="input-field md:col-span-1"
            >
              <option value="">Select provider…</option>
              {Array.from(new Set((settings?.available_models ?? []).map(opt => opt.provider))).map(provider => (
                <option key={provider} value={provider}>{provider}</option>
              ))}
            </select>
            <input
              type="password"
              value={defaultKeyValue}
              onChange={e => setDefaultKeyValue(e.target.value)}
              placeholder="API Key (sk-…)"
              className="input-field md:col-span-1"
            />
            <button
              onClick={handleSetDefaultKey}
              disabled={defaultKeySaving || !defaultKeyProvider || !defaultKeyValue.trim()}
              className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm disabled:opacity-50"
            >
              {defaultKeySaving ? 'Saving…' : 'Save Key'}
            </button>
          </div>
        </div>

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
