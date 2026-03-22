import { FileText, LogOut, MessageSquare, Plus, Settings, ShieldCheck, SlidersHorizontal, Trash2, UserX } from 'lucide-react'
import type { Conversation, CurrentUser } from '../../types'

interface Props {
  conversations: Conversation[]
  activeConversationId?: string
  currentUser: CurrentUser | null
  impersonatingUserEmail: string | null
  onStopImpersonating: () => void
  onSelectConversation: (conv: Conversation) => void
  onNewConversation: () => void
  onDeleteConversation: (id: string) => void
  onManageAgents: () => void
  onOpenSettings: () => void
  onOpenAudit: () => void
  onLogout: () => void
  onOpenAdmin?: () => void
}

export default function Sidebar({
  conversations,
  activeConversationId,
  currentUser,
  impersonatingUserEmail,
  onStopImpersonating,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onManageAgents,
  onOpenSettings,
  onOpenAudit,
  onLogout,
  onOpenAdmin,
}: Props) {
  return (
    <aside className="w-64 bg-gray-800 flex flex-col border-r border-gray-700">
      {/* Impersonation banner */}
      {impersonatingUserEmail && (
        <div className="bg-amber-600 px-3 py-2 flex items-center justify-between gap-2 text-xs text-white">
          <span className="truncate">Acting as: <strong>{impersonatingUserEmail}</strong></span>
          <button
            onClick={onStopImpersonating}
            className="shrink-0 hover:text-amber-200 transition-colors"
            title="Stop impersonating"
          >
            <UserX size={14} />
          </button>
        </div>
      )}

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
      <div className="p-3 border-t border-gray-700 space-y-1">
        {/* Credits badge — visible to all users */}
        {currentUser && (
          <div className="px-3 py-1.5 text-xs text-gray-400 flex justify-between">
            <span>Credits</span>
            <span className={currentUser.credits <= 10 ? 'text-red-400 font-semibold' : 'text-gray-300 font-semibold'}>
              {currentUser.role === 'admin' && !impersonatingUserEmail ? '∞' : currentUser.credits}
            </span>
          </div>
        )}
        {currentUser?.role === 'admin' && !impersonatingUserEmail && (
          <div className="px-3 py-1.5 text-xs text-amber-400 font-semibold">Admin</div>
        )}

        <button
          onClick={onManageAgents}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm text-gray-300"
        >
          <Settings size={16} />
          Manage Agents
        </button>
        {!impersonatingUserEmail && (
          <>
            <button
              onClick={onOpenSettings}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm text-gray-300"
            >
              <SlidersHorizontal size={16} />
              Settings
            </button>
            <button
              onClick={onOpenAudit}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm text-gray-300"
            >
              <FileText size={16} />
              Audit
            </button>
            {onOpenAdmin && (
              <button
                onClick={onOpenAdmin}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm text-amber-400"
              >
                <ShieldCheck size={16} />
                Admin Panel
              </button>
            )}
          </>
        )}
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm text-red-300"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </aside>
  )
}
