import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { apiFetch, clearToken, getToken, setToken } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }
    apiFetch('/api/v1/auth/me', { withAuth: true })
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    })
    if (!res.ok) {
      throw new Error('Email hoặc mật khẩu không đúng')
    }
    const data = await res.json()
    setToken(data.access_token)
    const me = await apiFetch('/api/v1/auth/me')
    setUser(me)
  }, [])

  const register = useCallback(async ({ email, displayName, password }) => {
    const res = await apiFetch('/api/v1/auth/register', {
      method: 'POST',
      withAuth: false,
      body: { email, display_name: displayName, password },
    })
    setToken(res.access_token)
    const me = await apiFetch('/api/v1/auth/me')
    setUser(me)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}