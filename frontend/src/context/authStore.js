import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { API } from '../services/api'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      login: async (email, password) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
          })

          if (!response.ok) {
            throw new Error('Login failed')
          }

          const data = await response.json()
          set({ user: data.user, token: data.token, isLoading: false })
          return true
        } catch (error) {
          set({ error: error.message, isLoading: false })
          return false
        }
      },

      register: async (email, password, username, fullName) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, username, full_name: fullName })
          })

          if (!response.ok) {
            throw new Error('Registration failed')
          }

          const data = await response.json()
          set({ isLoading: false })
          return true
        } catch (error) {
          set({ error: error.message, isLoading: false })
          return false
        }
      },

      logout: async () => {
        // Notify backend for activity logging
        const currentToken = get().token
        if (currentToken) {
          fetch(`${API}/api/auth/logout`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${currentToken}` }
          }).catch(() => {}) // Fire-and-forget
        }
        set({ user: null, token: null })
      },

      setUser: (user) => set({ user }),
      setToken: (token) => set({ token }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, token: state.token })
    }
  )
)
