import { useEffect } from 'react'
import { socketService } from '../services/socket.service'
import { useAuthStore } from '../store/authStore'

export const useSocket = () => {
  const { token, isAuthenticated } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated && token) {
      socketService.connect(token)

      return () => {
        socketService.disconnect()
      }
    }
  }, [isAuthenticated, token])

  return socketService
}