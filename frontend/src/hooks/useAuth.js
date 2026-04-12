import { useAuthStore } from '../store/authStore'
import api from '../api/client'

export function useAuth() {
  const { token, role, username, setAuth, clearAuth } = useAuthStore()

  const login = async (usernameInput, password) => {
    const resp = await api.post('/auth/login', { username: usernameInput, password })
    setAuth(resp.data.access_token, resp.data.role, resp.data.username)
    return resp.data
  }

  const logout = () => {
    clearAuth()
    window.location.href = '/login'
  }

  const isAdmin = role === 'ADMIN'
  const isAnalyst = role === 'ADMIN' || role === 'ANALYST'

  return { token, role, username, login, logout, isAdmin, isAnalyst }
}
