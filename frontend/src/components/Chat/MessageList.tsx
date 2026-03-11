import React from 'react'
import type { Message, EphemeralMessage } from '../../types'

interface Props {
  messages: Message[]
  ephemeral: Record<string, EphemeralMessage>
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

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'} mb-4`}>
      {!isUser && msg.agent_name && (
        <AgentBadge name={msg.agent_name} />
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

export default function MessageList({ messages, ephemeral }: Props) {
  const bottomRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, ephemeral])

  const ephemeralEntries = Object.values(ephemeral)

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      {messages.map(msg => (
        <MessageBubble key={msg.id} msg={msg} />
      ))}
      {ephemeralEntries.map(e => (
        <StreamingBubble key={e.agent} msg={e} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
