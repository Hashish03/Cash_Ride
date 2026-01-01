import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Phone, X, MapPin, Clock, User } from 'lucide-react'
import Header from '../../components/layout/Header'
import Button from '../../components/common/Button'
import MapView from '../../components/maps/MapView'
import DriverCard from '../../components/ride/DriverCard'
import Modal from '../../components/common/Modal'
import { rideService } from '../../services/ride.service'
import { useSocket } from '../../hooks/useSocket'
import { RIDE_STATUS } from '../../utils/constants'

export function RideTracking() {
  const { rideId } = useParams()
  const navigate = useNavigate()
  const socket = useSocket()
  const [ride, setRide] = useState(null)
  const [driver, setDriver] = useState(null)
  const [showCancelModal, setShowCancelModal] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadRideDetails()
    
    // Listen for real-time updates
    socket.on(`ride_${rideId}_update`, (data) => {
      setRide(prev => ({ ...prev, ...data }))
    })

    socket.on(`driver_${ride?.driver_id}_location`, (location) => {
      setDriver(prev => ({ ...prev, location }))
    })

    return () => {
      socket.off(`ride_${rideId}_update`)
      socket.off(`driver_${ride?.driver_id}_location`)
    }
  }, [rideId])

  const loadRideDetails = async () => {
    try {
      const data = await rideService.getRideStatus(rideId)
      setRide(data.ride)
      setDriver(data.driver)
    } catch (error) {
      console.error('Failed to load ride:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCancelRide = async () => {
    try {
      await rideService.cancelRide(rideId)
      navigate('/')
    } catch (error) {
      console.error('Failed to cancel ride:', error)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  if (!ride) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="bg-white rounded-xl p-8 text-center">
            <p className="text-gray-600">Ride not found</p>
            <Button onClick={() => navigate('/')} className="mt-4">
              Go Home
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Map */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
              <div className="h-[500px]">
                <MapView
                  center={driver?.location || { lat: ride.pickup_latitude, lng: ride.pickup_longitude }}
                  markers={[
                    { position: { lat: ride.pickup_latitude, lng: ride.pickup_longitude }, title: 'Pickup' },
                    { position: { lat: ride.destination_latitude, lng: ride.destination_longitude }, title: 'Destination' },
                  ]}
                />
              </div>
            </div>
          </div>

          {/* Ride Info */}
          <div className="space-y-6">
            {/* Status */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Ride Status</h2>
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  {ride.status}
                </span>
              </div>

              <div className="space-y-4">
                {ride.status === RIDE_STATUS.REQUESTED && (
                  <div className="text-center py-4">
                    <div className="animate-pulse">
                      <Clock className="mx-auto text-primary-600 mb-2" size={32} />
                      <p className="text-gray-600">Finding you a driver...</p>
                    </div>
                  </div>
                )}

                {ride.status === RIDE_STATUS.ACCEPTED && driver && (
                  <div>
                    <p className="text-sm text-gray-600 mb-4">Your driver is on the way</p>
                    <DriverCard driver={driver} />
                  </div>
                )}

                {ride.status === RIDE_STATUS.IN_PROGRESS && (
                  <div className="text-center py-4">
                    <MapPin className="mx-auto text-primary-600 mb-2" size={32} />
                    <p className="font-medium">En route to destination</p>
                  </div>
                )}
              </div>

              {/* Cancel Button */}
              {(ride.status === RIDE_STATUS.REQUESTED || ride.status === RIDE_STATUS.ACCEPTED) && (
                <Button
                  variant="danger"
                  onClick={() => setShowCancelModal(true)}
                  className="w-full mt-4"
                >
                  <X size={18} />
                  Cancel Ride
                </Button>
              )}
            </div>

            {/* Trip Details */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="font-semibold mb-4">Trip Details</h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <MapPin className="text-primary-600 mt-1" size={18} />
                  <div>
                    <p className="text-sm text-gray-500">Pickup</p>
                    <p className="text-sm font-medium">{ride.pickup_address}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <MapPin className="text-red-600 mt-1" size={18} />
                  <div>
                    <p className="text-sm text-gray-500">Destination</p>
                    <p className="text-sm font-medium">{ride.destination_address}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Cancel Confirmation Modal */}
      <Modal
        isOpen={showCancelModal}
        onClose={() => setShowCancelModal(false)}
        title="Cancel Ride"
      >
        <div className="space-y-4">
          <p className="text-gray-600">Are you sure you want to cancel this ride?</p>
          <div className="flex gap-4">
            <Button
              variant="secondary"
              onClick={() => setShowCancelModal(false)}
              className="flex-1"
            >
              Keep Ride
            </Button>
            <Button
              variant="danger"
              onClick={handleCancelRide}
              className="flex-1"
            >
              Yes, Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}