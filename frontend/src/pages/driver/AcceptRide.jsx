import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Navigation, Phone, CheckCircle } from 'lucide-react'
import Header from '../../components/layout/Header'
import Button from '../../components/common/Button'
import MapView from '../../components/maps/MapView'
import { rideService } from '../../services/ride.service'

export function AcceptRide() {
  const { rideId } = useParams()
  const navigate = useNavigate()
  const [ride, setRide] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadRideDetails()
  }, [rideId])

  const loadRideDetails = async () => {
    try {
      const data = await rideService.getRideStatus(rideId)
      setRide(data.ride)
    } catch (error) {
      console.error('Failed to load ride:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleStartRide = async () => {
    try {
      await rideService.startRide(rideId)
      setRide({ ...ride, status: 'in_progress' })
    } catch (error) {
      console.error('Failed to start ride:', error)
    }
  }

  const handleCompleteRide = async () => {
    try {
      await rideService.completeRide(rideId)
      navigate('/driver/dashboard')
    } catch (error) {
      console.error('Failed to complete ride:', error)
    }
  }

  if (loading || !ride) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
              <div className="h-[500px]">
                <MapView
                  center={{ lat: ride.pickup_latitude, lng: ride.pickup_longitude }}
                  markers={[
                    { position: { lat: ride.pickup_latitude, lng: ride.pickup_longitude }, title: 'Pickup' },
                    { position: { lat: ride.destination_latitude, lng: ride.destination_longitude }, title: 'Destination' },
                  ]}
                />
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="text-lg font-semibold mb-4">Ride Details</h2>
              
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-500">Passenger</p>
                  <p className="font-medium">{ride.passenger?.first_name} {ride.passenger?.last_name}</p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Pickup Location</p>
                  <p className="text-sm font-medium">{ride.pickup_address}</p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Destination</p>
                  <p className="text-sm font-medium">{ride.destination_address}</p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Fare</p>
                  <p className="text-2xl font-bold text-primary-600">${ride.fare_amount}</p>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <Button variant="outline" className="flex-1">
                  <Phone size={18} />
                  Call
                </Button>
                <Button variant="outline" className="flex-1">
                  <Navigation size={18} />
                  Navigate
                </Button>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border p-6">
              {ride.status === 'accepted' && (
                <Button onClick={handleStartRide} className="w-full">
                  Start Ride
                </Button>
              )}
              
              {ride.status === 'in_progress' && (
                <Button onClick={handleCompleteRide} className="w-full">
                  <CheckCircle size={18} />
                  Complete Ride
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}