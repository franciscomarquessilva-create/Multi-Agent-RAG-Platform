import React from 'react'
import type { Message, EphemeralMessage } from '../../types'

interface Props {
  messages: Message[]
  ephemeral: Record<string, EphemeralMessage>
  processingTargets?: string[]
}

function AgentBadge({ name, isOrchestrator }: { name: string; isOrchestrator?: boolean }) {
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
      isOrchestrator ? 'bg-blue-700 text-blue-100' : 'bg-emerald-700 text-emerald-100'
    }`}>
      {name}
    </span>
  )
}

function InternalMessageBox({
  title,
  content,
  createdAt,
  isStreaming = false,
}: {
  title: string
  content: string
  createdAt?: string
  isStreaming?: boolean
}) {
  return (
    <div className="flex flex-col gap-1 items-start mb-4">
      <details className="max-w-3xl w-full rounded-2xl border border-amber-500/30 bg-gray-800/80 overflow-hidden">
        <summary className="cursor-pointer px-4 py-3 text-sm text-amber-100 flex items-center gap-3">
          <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-300">Internal</span>
          <span className="font-medium">{title}</span>
        </summary>
        <div className="border-t border-amber-500/20 px-4 py-3 text-sm text-gray-200 whitespace-pre-wrap break-words bg-gray-900/50">
          {content}
          {isStreaming && <span className="streaming-cursor" />}
        </div>
      </details>
      {createdAt && (
        <span className="text-xs text-gray-500">
          {new Date(createdAt).toLocaleTimeString()}
        </span>
      )}
    </div>
  )
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  const userTargetLabel = isUser && msg.mode
    ? (msg.agent_name || (msg.mode === 'orchestrator' ? 'Orchestrator' : 'Selected slaves'))
    : null

  if (!isUser && msg.message_type === 'internal') {
    return (
      <InternalMessageBox
        title={msg.agent_name || 'Internal exchange'}
        content={msg.content}
        createdAt={msg.created_at}
      />
    )
  }

  return (
    <div className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'} mb-4`}>
      {!isUser && msg.agent_name && (
        <AgentBadge name={msg.agent_name} />
      )}
      {isUser && userTargetLabel && (
        <span className="text-xs text-blue-300">To: {userTargetLabel}</span>
      )}
      <div
        className={`max-w-2xl px-4 py-2 rounded-2xl text-sm whitespace-pre-wrap break-words ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-gray-700 text-gray-100 rounded-bl-sm'
        }`}
      >
        {msg.content}
      </div>
      <span className="text-xs text-gray-500">
        {new Date(msg.created_at).toLocaleTimeString()}
      </span>
    </div>
  )
}

function StreamingBubble({ msg }: { msg: EphemeralMessage }) {
  if (msg.message_type === 'internal') {
    return (
      <InternalMessageBox
        title={msg.agent}
        content={msg.content}
        isStreaming={msg.isStreaming}
      />
    )
  }

  return (
    <div className="flex flex-col gap-1 items-start mb-4">
      <AgentBadge name={msg.agent} />
      <div className="max-w-2xl px-4 py-2 rounded-2xl rounded-bl-sm text-sm bg-gray-700 text-gray-100 whitespace-pre-wrap break-words">
        {msg.content}
        {msg.isStreaming && <span className="streaming-cursor" />}
      </div>
    </div>
  )
}

function ProcessingBubble({ agent }: { agent: string }) {
  return (
    <div className="flex flex-col gap-1 items-start mb-4">
      <AgentBadge name={agent} />
      <div className="max-w-2xl px-4 py-2 rounded-2xl rounded-bl-sm text-sm bg-gray-800 text-gray-300 border border-gray-700">
        Thinking
        <span className="thinking-dots" aria-hidden="true">
          <span>.</span><span>.</span><span>.</span>
        </span>
      </div>
    </div>
  )
}

export default function MessageList({ messages, ephemeral, processingTargets = [] }: Props) {
  const bottomRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, ephemeral])

  const ephemeralEntries = Object.values(ephemeral)
  const ephemeralAgents = new Set(ephemeralEntries.map(e => e.agent))
  const pendingTargets = processingTargets.filter(name => !ephemeralAgents.has(name))

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      {messages.map(msg => (
        <MessageBubble key={msg.id} msg={msg} />
      ))}
      {pendingTargets.map(name => (
        <ProcessingBubble key={`processing-${name}`} agent={name} />
      ))}
      {ephemeralEntries.map(e => (
        <StreamingBubble key={e.key} msg={e} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
