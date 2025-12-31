import api from './api'

export const rideService = {
  async requestRide(rideData) {
    const response = await api.post('/rides/request', rideData)
    return response.data
  },

  async getRideStatus(rideId) {
    const response = await api.get(`/rides/${rideId}/status`)
    return response.data
  },

  async cancelRide(rideId) {
    const response = await api.post(`/rides/${rideId}/cancel`)
    return response.data
  },

  async getRideHistory() {
    const response = await api.get('/rides/history')
    return response.data
  },

  async acceptRide(rideId) {
    const response = await api.post(`/rides/${rideId}/accept`)
    return response.data
  },

  async startRide(rideId) {
    const response = await api.post(`/rides/${rideId}/start`)
    return response.data
  },

  async completeRide(rideId) {
    const response = await api.post(`/rides/${rideId}/complete`)
    return response.data
  },

  async estimateFare(pickupLocation, dropoffLocation) {
    const response = await api.post('/location/estimate-fare', {
      pickup_latitude: pickupLocation.lat,
      pickup_longitude: pickupLocation.lng,
      destination_latitude: dropoffLocation.lat,
      destination_longitude: dropoffLocation.lng,
    })
    return response.data
  },
}