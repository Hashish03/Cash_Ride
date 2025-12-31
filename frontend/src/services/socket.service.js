import { io } from 'socket.io-client'

class SocketService {
  constructor() {
    this.socket = null
  }

  connect(token) {
    this.socket = io(import.meta.env.VITE_SOCKET_URL, {
      auth: {
        token: token,
      },
    })

    this.socket.on('connect', () => {
      console.log('Socket connected:', this.socket.id)
    })

    this.socket.on('disconnect', () => {
      console.log('Socket disconnected')
    })

    return this.socket
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  emit(event, data) {
    if (this.socket) {
      this.socket.emit(event, data)
    }
  }

  on(event, callback) {
    if (this.socket) {
      this.socket.on(event, callback)
    }
  }

  off(event) {
    if (this.socket) {
      this.socket.off(event)
    }
  }
}

export const socketService = new SocketService()