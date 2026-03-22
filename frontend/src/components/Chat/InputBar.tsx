import React, { useState } from 'react'
import { Send } from 'lucide-react'

interface Props {
  orchestratorMode?: 'broadcast' | 'orchestrate' | 'mediator' | null
  onSend: (payload: { content: string; iterations?: number; broadcastInstructions?: string; orchestratorInstructions?: string }) => void
  disabled: boolean
}

export default function InputBar({
  orchestratorMode,
  onSend,
  disabled,
}: Props) {
  const [text, setText] = useState('')
  const [broadcastText, setBroadcastText] = useState('')
  const [orchestratorText, setOrchestratorText] = useState('')
  const [iterations, setIterations] = useState(1)

  const isBroadcast = orchestratorMode === 'broadcast'
  const isMediator = orchestratorMode === 'mediator'

  const handleSend = () => {
    if (disabled) return

    if (isBroadcast) {
      const broadcastInstructions = broadcastText.trim()
      const orchestratorInstructions = orchestratorText.trim()
      if (!broadcastInstructions && !orchestratorInstructions) return

      const contentParts = []
      if (broadcastInstructions) contentParts.push(`Broadcast instructions:\n${broadcastInstructions}`)
      if (orchestratorInstructions) contentParts.push(`Orchestrator instructions:\n${orchestratorInstructions}`)

      onSend({
        content: contentParts.join('\n\n'),
        broadcastInstructions,
        orchestratorInstructions,
      })
      setBroadcastText('')
      setOrchestratorText('')
      return
    }

    if (isMediator) {
      const discussionTopic = text.trim()
      const mediatorInstructions = orchestratorText.trim()
      if (!discussionTopic) return
      onSend({
        content: discussionTopic,
        iterations,
        orchestratorInstructions: mediatorInstructions || undefined,
      })
      setText('')
      setOrchestratorText('')
      return
    }

    const trimmed = text.trim()
    if (!trimmed) return
    onSend({ content: trimmed, iterations })
    setText('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-gray-700 px-4 py-3 bg-gray-800">
      {/* Orchestrator controls */}
      <div className="flex items-center gap-2 mb-2">
        {!isBroadcast && (
          <div className="ml-auto flex items-center gap-2">
          <label className="text-xs text-gray-400" htmlFor="iterations-input">Max iterations</label>
          <input
            id="iterations-input"
            type="number"
            min={1}
            max={10}
            value={iterations}
            onChange={e => {
              const next = Number.parseInt(e.target.value, 10)
              if (Number.isNaN(next)) {
                setIterations(1)
                return
              }
              setIterations(Math.max(1, Math.min(10, next)))
            }}
            className="w-16 bg-gray-700 text-gray-100 rounded-lg px-2 py-1 text-xs border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-2 items-end">
        <div className="flex-1 space-y-2">
          {isBroadcast ? (
            <>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Broadcast instructions</label>
                <textarea
                  value={broadcastText}
                  onChange={e => setBroadcastText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Only these instructions are sent to slave agents..."
                  disabled={disabled}
                  rows={3}
                  className="w-full bg-gray-700 text-gray-100 placeholder-gray-500 rounded-xl px-4 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Orchestrator instructions</label>
                <textarea
                  value={orchestratorText}
                  onChange={e => setOrchestratorText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Instructions to be followed only by the orchestrator..."
                  disabled={disabled}
                  rows={3}
                  className="w-full bg-gray-700 text-gray-100 placeholder-gray-500 rounded-xl px-4 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
              </div>
            </>
          ) : isMediator ? (
            <>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Discussion topic</label>
                <textarea
                  value={text}
                  onChange={e => setText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Topic for the two slave agents to debate..."
                  disabled={disabled}
                  rows={3}
                  className="w-full bg-gray-700 text-gray-100 placeholder-gray-500 rounded-xl px-4 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Mediator instructions (private)</label>
                <textarea
                  value={orchestratorText}
                  onChange={e => setOrchestratorText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Only the mediator sees this text. Slave agents do not."
                  disabled={disabled}
                  rows={3}
                  className="w-full bg-gray-700 text-gray-100 placeholder-gray-500 rounded-xl px-4 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
              </div>
            </>
          ) : (
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message orchestrator..."
              disabled={disabled}
              rows={1}
              className="w-full bg-gray-700 text-gray-100 placeholder-gray-500 rounded-xl px-4 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 max-h-32 overflow-y-auto"
              style={{ minHeight: '40px' }}
            />
          )}
        </div>
        <button
          onClick={handleSend}
          disabled={disabled || (isBroadcast ? (!broadcastText.trim() && !orchestratorText.trim()) : !text.trim())}
          className="p-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
