import React, { createContext, useContext, useState, useCallback } from 'react'
import { authApi } from '../api/auth.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('nhis_token'))
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('nhis_user') || 'null') } catch { return null }
  })

  const saveSession = useCallback((data) => {
    localStorage.setItem('nhis_token', data.access_token)
    localStorage.setItem('nhis_user', JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await authApi.login({ email, password })
    saveSession(data)
    return data.user
  }, [saveSession])

  const register = useCallback(async (formData) => {
    const data = await authApi.register(formData)
    saveSession(data)
    return data.user
  }, [saveSession])

  const logout = useCallback(async () => {
    try { await authApi.logout() } catch {}
    localStorage.removeItem('nhis_token')
    localStorage.removeItem('nhis_user')
    setToken(null)
    setUser(null)
  }, [])

  const updateUser = useCallback((updatedUser) => {
    localStorage.setItem('nhis_user', JSON.stringify(updatedUser))
    setUser(updatedUser)
  }, [])

  return (
    <AuthContext.Provider value={{ token, user, login, register, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
