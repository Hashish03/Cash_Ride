import { useState, useEffect } from 'react'
import { useLocationStore } from '../store/locationStore'

export const useGeolocation = () => {
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const { currentLocation, setCurrentLocation } = useLocationStore()

  useEffect(() => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported')
      setLoading(false)
      return
    }

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        setCurrentLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        })
        setLoading(false)
        setError(null)
      },
      (err) => {
        setError(err.message)
        setLoading(false)
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      }
    )

    return () => navigator.geolocation.clearWatch(watchId)
  }, [setCurrentLocation])

  return { currentLocation, loading, error }
}