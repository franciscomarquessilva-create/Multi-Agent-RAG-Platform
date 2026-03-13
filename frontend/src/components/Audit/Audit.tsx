import { useEffect, useState } from 'react'
import { ChevronLeft, RefreshCcw, Trash2 } from 'lucide-react'
import type { ClientAuditTrace } from '../../types'
import { clearClientAuditTraces, getClientAuditTraces } from '../../services/auditTrace'

interface LLMLogItem {
  id: string
  agent_name: string
  model: string
  request_payload: string
  response_payload: string | null
  error: string | null
  created_at: string
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface Props {
  onBack: () => void
}

export default function Audit({ onBack }: Props) {
  const [logs, setLogs] = useState<LLMLogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [clientTraces, setClientTraces] = useState<ClientAuditTrace[]>([])

  const loadLogs = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${BASE_URL}/logs/llm?limit=300`)
      if (!response.ok) {
        const detail = await response.text()
        throw new Error(`HTTP ${response.status}${detail ? ` - ${detail}` : ''}`)
      }
      const data = await response.json() as LLMLogItem[]
      setLogs(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load LLM logs')
    } finally {
      setLoading(false)
    }
    setClientTraces(getClientAuditTraces(300))
  }

  useEffect(() => {
    loadLogs()
  }, [])

  const handleClearClientTraces = () => {
    clearClientAuditTraces()
    setClientTraces([])
  }

  return (
    <div className="flex flex-col h-full bg-gray-900">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-700">
        <button onClick={onBack} className="p-1 rounded hover:bg-gray-700 transition-colors">
          <ChevronLeft size={20} />
        </button>
        <h2 className="text-lg font-semibold">Audit</h2>
        <button
          onClick={loadLogs}
          className="ml-auto flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
        >
          <RefreshCcw size={14} />
          Refresh
        </button>
        <button
          onClick={handleClearClientTraces}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
        >
          <Trash2 size={14} />
          Clear Traces
        </button>
      </div>

      <div className="p-4 overflow-y-auto flex-1 space-y-3">
        <div className="rounded-xl border border-cyan-800/50 bg-cyan-950/20 p-3">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-cyan-200">Client Stream Trace</h3>
            <span className="text-xs text-cyan-300/80">{clientTraces.length} events</span>
          </div>
          {clientTraces.length === 0 ? (
            <p className="text-xs text-cyan-300/70">No client trace events yet.</p>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {clientTraces.map(trace => (
                <div key={trace.id} className="rounded border border-cyan-900/60 bg-gray-900/60 p-2">
                  <div className="flex flex-wrap gap-2 items-center text-[11px]">
                    <span className="px-1.5 py-0.5 rounded bg-cyan-900/60 text-cyan-200">{trace.stage}</span>
                    {trace.conversation_id && (
                      <span className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-300">conv {trace.conversation_id.slice(0, 8)}</span>
                    )}
                    <span className="text-gray-400">{new Date(trace.created_at).toLocaleTimeString()}</span>
                  </div>
                  {trace.details && (
                    <pre className="mt-1 text-xs bg-gray-900 border border-gray-700 rounded p-2 overflow-x-auto text-gray-200 whitespace-pre-wrap">
                      {trace.details}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {loading && <p className="text-sm text-gray-400">Loading logs...</p>}
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!loading && !error && logs.length === 0 && (
          <p className="text-sm text-gray-500">No LLM logs found yet.</p>
        )}

        {logs.map(log => (
          <div key={log.id} className="rounded-xl border border-gray-700 bg-gray-800 p-3">
            <div className="flex flex-wrap gap-2 items-center mb-2 text-xs">
              <span className="px-2 py-0.5 rounded bg-blue-800/60 text-blue-200">{log.agent_name}</span>
              <span className="px-2 py-0.5 rounded bg-gray-700 text-gray-200">{log.model}</span>
              <span className="text-gray-400">{new Date(log.created_at).toLocaleString()}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-gray-400 mb-1">Request</p>
                <pre className="text-xs bg-gray-900 border border-gray-700 rounded p-2 overflow-x-auto text-gray-200 whitespace-pre-wrap">
                  {log.request_payload}
                </pre>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Response</p>
                <pre className="text-xs bg-gray-900 border border-gray-700 rounded p-2 overflow-x-auto text-gray-200 whitespace-pre-wrap">
                  {log.response_payload || '(empty)'}
                </pre>
              </div>
            </div>

            {log.error && (
              <p className="mt-2 text-xs text-red-300 bg-red-950/30 border border-red-900 rounded p-2">
                Error: {log.error}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
