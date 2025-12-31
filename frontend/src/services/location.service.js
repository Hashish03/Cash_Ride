import api from './api'

export const locationService = {
  async updateLocation(latitude, longitude) {
    const response = await api.post('/location/update', {
      latitude,
      longitude,
    })
    return response.data
  },

  async getNearbyDrivers(latitude, longitude) {
    const response = await api.get('/location/nearby-drivers', {
      params: { latitude, longitude },
    })
    return response.data
  },

  async getRoute(origin, destination) {
    const response = await api.get('/location/route', {
      params: {
        origin_lat: origin.lat,
        origin_lng: origin.lng,
        dest_lat: destination.lat,
        dest_lng: destination.lng,
      },
    })
    return response.data
  },

  getCurrentPosition() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported'))
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          })
        },
        (error) => {
          reject(error)
        },
        {
          enableHighAccuracy: true,
          timeout: 5000,
          maximumAge: 0,
        }
      )
    })
  },
}