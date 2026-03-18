import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { CurrentUser } from '../types'
import { getMe, setImpersonationHeader } from '../services/api'

interface AuthContextValue {
  currentUser: CurrentUser | null
  isLoading: boolean
  authError: string | null
  impersonatingUserId: string | null
  impersonatingUserEmail: string | null
  impersonate: (userId: string, userEmail: string) => void
  stopImpersonating: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [authError, setAuthError] = useState<string | null>(null)
  const [impersonatingUserId, setImpersonatingUserId] = useState<string | null>(null)
  const [impersonatingUserEmail, setImpersonatingUserEmail] = useState<string | null>(null)

  const refreshUser = useCallback(async () => {
    try {
      const user = await getMe()
      setCurrentUser(user)
      setAuthError(null)
    } catch (err: unknown) {
      setCurrentUser(null)
      const maybeAxios = err as { response?: { data?: { detail?: string } } }
      const detail = maybeAxios.response?.data?.detail
      setAuthError(typeof detail === 'string' ? detail : 'Authentication required')
    }
  }, [])

  useEffect(() => {
    refreshUser().finally(() => setIsLoading(false))
  }, [refreshUser])

  const impersonate = useCallback((userId: string, userEmail: string) => {
    setImpersonatingUserId(userId)
    setImpersonatingUserEmail(userEmail)
    setImpersonationHeader(userId)
  }, [])

  const stopImpersonating = useCallback(() => {
    setImpersonatingUserId(null)
    setImpersonatingUserEmail(null)
    setImpersonationHeader(null)
  }, [])

  return (
    <AuthContext.Provider value={{
      currentUser,
      isLoading,
      authError,
      impersonatingUserId,
      impersonatingUserEmail,
      impersonate,
      stopImpersonating,
      refreshUser,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
