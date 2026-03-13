import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, Save } from 'lucide-react'
import type { AppSettings, ModelOption, PromptConfigItem } from '../../types'
import { updateAppSettings, updatePromptConfig } from '../../services/api'

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
        <div>
          <h3 className="text-sm font-semibold text-gray-200">Allowed Models</h3>
          <p className="text-sm text-gray-400 mt-1">
            Select which models agents are allowed to use. OpenAI, Anthropic, Gemini and Grok options are included here.
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
