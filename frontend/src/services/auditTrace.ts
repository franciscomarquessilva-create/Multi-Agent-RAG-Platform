import type { ClientAuditTrace } from '../types'

const STORAGE_KEY = 'client_audit_traces'
const MAX_TRACES = 300

function safeRead(): ClientAuditTrace[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return []
    }
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed.filter(item => item && typeof item === 'object') as ClientAuditTrace[]
  } catch {
    return []
  }
}

function safeWrite(items: ClientAuditTrace[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, MAX_TRACES)))
  } catch {
    // Ignore localStorage errors to avoid breaking message send flow.
  }
}

export function appendClientAuditTrace(
  trace: Omit<ClientAuditTrace, 'id' | 'created_at'> & { id?: string; created_at?: string }
): void {
  const item: ClientAuditTrace = {
    id: trace.id ?? `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    stage: trace.stage,
    details: trace.details ?? null,
    conversation_id: trace.conversation_id ?? null,
    created_at: trace.created_at ?? new Date().toISOString(),
  }
  const next = [item, ...safeRead()]
  safeWrite(next)
}

export function getClientAuditTraces(limit = 200): ClientAuditTrace[] {
  return safeRead().slice(0, limit)
}

export function clearClientAuditTraces(): void {
  safeWrite([])
}