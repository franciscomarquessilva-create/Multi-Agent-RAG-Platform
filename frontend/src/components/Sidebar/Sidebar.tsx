import { FileText, MessageSquare, Plus, Settings, SlidersHorizontal, Trash2 } from 'lucide-react'
import type { Conversation } from '../../types'

interface Props {
  conversations: Conversation[]
  activeConversationId?: string
  onSelectConversation: (conv: Conversation) => void
  onNewConversation: () => void
  onDeleteConversation: (id: string) => void
  onManageAgents: () => void
  onOpenSettings: () => void
  onOpenAudit: () => void
}

export default function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onManageAgents,
  onOpenSettings,
  onOpenAudit,
}: Props) {
  return (
    <aside className="w-64 bg-gray-800 flex flex-col border-r border-gray-700">
      {/* Header */}
      <div className="p-3 border-b border-gray-700">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto py-2">
        {conversations.length === 0 && (
          <p className="px-3 py-4 text-gray-500 text-sm text-center">No conversations yet</p>
        )}
        {conversations.map(conv => (
          <div
            key={conv.id}
            className={`group flex items-center gap-2 px-3 py-2 mx-1 rounded-lg cursor-pointer transition-colors ${
              conv.id === activeConversationId
                ? 'bg-gray-600'
                : 'hover:bg-gray-700'
            }`}
            onClick={() => onSelectConversation(conv)}
          >
            <MessageSquare size={14} className="text-gray-400 shrink-0" />
            <span className="flex-1 text-sm text-gray-200 truncate">{conv.title}</span>
            <button
              onClick={e => { e.stopPropagation(); onDeleteConversation(conv.id) }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-600 transition-all"
              title="Delete conversation"
            >
              <Trash2 size={12} className="text-gray-400 hover:text-red-400" />
            </button>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-700">
        <button
          onClick={onManageAgents}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm text-gray-300"
        >
          <Settings size={16} />
          Manage Agents
        </button>
        <button
          onClick={onOpenSettings}
          className="w-full mt-2 flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm text-gray-300"
        >
          <SlidersHorizontal size={16} />
          Settings
        </button>
        <button
          onClick={onOpenAudit}
          className="w-full mt-2 flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm text-gray-300"
        >
          <FileText size={16} />
          Audit
        </button>
      </div>
    </aside>
  )
}
