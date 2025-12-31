import { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'

export default function MapView({ center, markers = [], routes = [] }) {
  const mapRef = useRef(null)
  const [map, setMap] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Initialize map
    if (!window.google) {
      console.error('Google Maps not loaded')
      setLoading(false)
      return
    }

    const mapInstance = new window.google.maps.Map(mapRef.current, {
      center: center || { lat: 40.7128, lng: -74.0060 },
      zoom: 13,
      disableDefaultUI: false,
      zoomControl: true,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: false,
    })

    setMap(mapInstance)
    setLoading(false)
  }, [])

  useEffect(() => {
    if (!map) return

    // Update center
    if (center) {
      map.setCenter(center)
    }
  }, [map, center])

  useEffect(() => {
    if (!map) return

    // Clear existing markers
    // Add new markers
    markers.forEach((marker) => {
      new window.google.maps.Marker({
        position: marker.position,
        map: map,
        title: marker.title,
        icon: marker.icon,
      })
    })
  }, [map, markers])

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100">
        <Loader2 className="animate-spin text-primary-600" size={32} />
      </div>
    )
  }

  return <div ref={mapRef} className="w-full h-full rounded-lg" />
}