import { useState, useEffect } from 'react'
import { rideService } from '../../services/ride.service'
import RideCard from '../ride/RideCard'
import Spinner from '../common/spinner'

export default function RideHistory() {
  const [rides, setRides] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadRideHistory()
  }, [])

  const loadRideHistory = async () => {
    try {
      const data = await rideService.getRideHistory()
      setRides(data.rides)
    } catch (error) {
      console.error('Failed to load ride history:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <Spinner />
  }

  if (rides.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No ride history yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {rides.map((ride) => (
        <RideCard key={ride.id} ride={ride} />
      ))}
    </div>
  )
}