import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      role: null,
      username: null,
      setAuth: (token, role, username) => set({ token, role, username }),
      clearAuth: () => set({ token: null, role: null, username: null }),
    }),
    {
      name: 'ghostexodus-auth',
      partialize: (state) => ({ token: state.token, role: state.role, username: state.username }),
    }
  )
)
