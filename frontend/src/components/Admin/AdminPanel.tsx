import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Coins, RefreshCw, ShieldCheck, UserCheck, UserX } from 'lucide-react'
import type { UserSummary, UserUpdate } from '../../types'
import { listUsers, updateUser } from '../../services/api'
import { useAuth } from '../../contexts/AuthContext'

interface Props {
  onBack: () => void
  onUserChanged: () => void
}

export default function AdminPanel({ onBack, onUserChanged }: Props) {
  const { currentUser, impersonatingUserId, impersonatingUserEmail, impersonate, stopImpersonating } = useAuth()
  const [users, setUsers] = useState<UserSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creditInputs, setCreditInputs] = useState<Record<string, string>>({})
  const [savingId, setSavingId] = useState<string | null>(null)

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listUsers()
      setUsers(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadUsers() }, [loadUsers])

  const applyUpdate = async (userId: string, payload: UserUpdate) => {
    setSavingId(userId)
    try {
      const updated = await updateUser(userId, payload)
      setUsers(prev => prev.map(u => u.id === userId ? updated : u))
      onUserChanged()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Update failed')
    } finally {
      setSavingId(null)
    }
  }

  const handleRoleToggle = (user: UserSummary) => {
    applyUpdate(user.id, { role: user.role === 'admin' ? 'user' : 'admin' })
  }

  const handleBlockToggle = (user: UserSummary) => {
    applyUpdate(user.id, { is_blocked: !user.is_blocked })
  }

  const handleActivationToggle = (user: UserSummary) => {
    applyUpdate(user.id, { is_active: !user.is_active })
  }

  const handleCreditSet = (user: UserSummary) => {
    const val = parseInt(creditInputs[user.id] ?? '', 10)
    if (isNaN(val)) return
    applyUpdate(user.id, { credits: val })
    setCreditInputs(prev => { const n = { ...prev }; delete n[user.id]; return n })
  }

  const handleCreditsAdjust = (user: UserSummary, delta: number) => {
    applyUpdate(user.id, { credits_delta: delta })
  }

  const handleImpersonate = (user: UserSummary) => {
    impersonate(user.id, user.email)
    onBack()
  }

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-700">
        <button onClick={onBack} className="text-gray-400 hover:text-gray-200 transition-colors">
          <ArrowLeft size={20} />
        </button>
        <ShieldCheck size={20} className="text-amber-400" />
        <h1 className="text-lg font-semibold">Admin Panel</h1>
        <button onClick={loadUsers} className="ml-auto text-gray-400 hover:text-gray-200 transition-colors" title="Refresh">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Impersonation banner */}
      {impersonatingUserEmail && (
        <div className="bg-amber-700 px-6 py-2 flex items-center justify-between text-sm text-white">
          <span>Currently acting as: <strong>{impersonatingUserEmail}</strong></span>
          <button
            onClick={stopImpersonating}
            className="underline hover:text-amber-200 transition-colors"
          >
            Stop Impersonating
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading && <p className="text-gray-400">Loading users…</p>}
        {error && <p className="text-red-400">{error}</p>}

        {!loading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-2 pr-4">Email</th>
                  <th className="pb-2 pr-4">Role</th>
                  <th className="pb-2 pr-4">Credits</th>
                  <th className="pb-2 pr-4">Agent Limit</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => {
                  const isCurrentAdmin = user.id === currentUser?.id
                  const isImpersonating = user.id === impersonatingUserId
                  const saving = savingId === user.id
                  return (
                    <tr
                      key={user.id}
                      className={`border-b border-gray-800 ${isImpersonating ? 'bg-amber-900/20' : ''}`}
                    >
                      <td className="py-3 pr-4">
                        <span className="text-gray-200">{user.email}</span>
                        {isCurrentAdmin && <span className="ml-2 text-xs text-amber-400">(you)</span>}
                      </td>

                      {/* Role */}
                      <td className="py-3 pr-4">
                        <button
                          disabled={isCurrentAdmin || saving}
                          onClick={() => handleRoleToggle(user)}
                          className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                            user.role === 'admin'
                              ? 'bg-amber-600 hover:bg-amber-700 text-white'
                              : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          {user.role}
                        </button>
                      </td>

                      {/* Credits */}
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-1">
                          <button
                            disabled={saving}
                            onClick={() => handleCreditsAdjust(user, -10)}
                            className="px-1.5 py-0.5 rounded bg-gray-700 hover:bg-gray-600 text-xs disabled:opacity-50"
                            title="-10 credits"
                          >−</button>
                          <input
                            type="number"
                            value={creditInputs[user.id] ?? user.credits}
                            onChange={e => setCreditInputs(prev => ({ ...prev, [user.id]: e.target.value }))}
                            onBlur={() => handleCreditSet(user)}
                            onKeyDown={e => e.key === 'Enter' && handleCreditSet(user)}
                            className="w-16 text-center bg-gray-800 border border-gray-600 rounded px-1 py-0.5 text-xs focus:outline-none focus:border-blue-500"
                          />
                          <button
                            disabled={saving}
                            onClick={() => handleCreditsAdjust(user, 10)}
                            className="px-1.5 py-0.5 rounded bg-gray-700 hover:bg-gray-600 text-xs disabled:opacity-50"
                            title="+10 credits"
                          >+</button>
                        </div>
                      </td>

                      {/* Agent Limit */}
                      <td className="py-3 pr-4 text-gray-300 text-xs">
                        {user.agent_limit === -1 ? '∞' : user.agent_limit}
                      </td>

                      {/* Status */}
                      <td className="py-3 pr-4">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          user.is_blocked
                            ? 'bg-red-800 text-red-200'
                            : user.is_active
                              ? 'bg-green-900 text-green-300'
                              : 'bg-amber-900 text-amber-300'
                        }`}>
                          {user.is_blocked ? 'blocked' : user.is_active ? 'active' : 'pending'}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          {/* Activate/deactivate */}
                          <button
                            disabled={isCurrentAdmin || saving}
                            onClick={() => handleActivationToggle(user)}
                            title={user.is_active ? 'Deactivate user' : 'Activate user'}
                            className="text-gray-400 hover:text-green-400 disabled:opacity-30 transition-colors"
                          >
                            {user.is_active ? <UserX size={15} /> : <UserCheck size={15} />}
                          </button>

                          {/* Block/unblock */}
                          <button
                            disabled={isCurrentAdmin || saving}
                            onClick={() => handleBlockToggle(user)}
                            title={user.is_blocked ? 'Unblock user' : 'Block user'}
                            className="text-gray-400 hover:text-red-400 disabled:opacity-30 transition-colors"
                          >
                            {user.is_blocked ? <UserCheck size={15} /> : <UserX size={15} />}
                          </button>

                          {/* Impersonate */}
                          {!isCurrentAdmin && (
                            <button
                              onClick={() => isImpersonating ? stopImpersonating() : handleImpersonate(user)}
                              title={isImpersonating ? 'Stop impersonating' : 'Impersonate user'}
                              className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded transition-colors ${
                                isImpersonating
                                  ? 'bg-amber-600 hover:bg-amber-700 text-white'
                                  : 'bg-gray-700 hover:bg-blue-600 text-gray-300 hover:text-white'
                              }`}
                            >
                              <Coins size={12} />
                              {isImpersonating ? 'Stop' : 'Impersonate'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
