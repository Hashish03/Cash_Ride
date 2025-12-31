import { useAuthStore } from '../store/authStore'
import { authService } from '../services/auth.service'
import { socketService } from '../services/socket.service'

export const useAuth = () => {
  const { user, token, isAuthenticated, login, logout } = useAuthStore()

  const handleLogin = async (email, password) => {
    try {
      const data = await authService.login(email, password)
      login(data.user, data.token)
      socketService.connect(data.token)
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.message || 'Login failed',
      }
    }
  }

  const handleLogout = async () => {
    try {
      await authService.logout()
      socketService.disconnect()
      logout()
    } catch (error) {
      console.error('Logout error:', error)
    }
  }

  return {
    user,
    token,
    isAuthenticated,
    login: handleLogin,
    logout: handleLogout,
  }
}