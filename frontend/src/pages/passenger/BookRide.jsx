import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin, DollarSign } from 'lucide-react'
import Header from '../../components/layout/Header'
import Button from '../../components/common/Button'
import LocationPicker from '../../components/maps/LocationPicker'
import { useLocationStore } from '../../store/locationStore'
import { useRideStore } from '../../store/rideStore'
import { rideService } from '../../services/ride.service'
import { formatCurrency } from '../../utils/helpers'

export function BookRide() {
  const navigate = useNavigate()
  const { pickupLocation, dropoffLocation, setPickupLocation, setDropoffLocation } = useLocationStore()
  const { setCurrentRide } = useRideStore()
  const [estimatedFare, setEstimatedFare] = useState(null)
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(1)

  const handleEstimateFare = async () => {
    if (!pickupLocation || !dropoffLocation) return

    setLoading(true)
    try {
      const data = await rideService.estimateFare(pickupLocation, dropoffLocation)
      setEstimatedFare(data.estimated_fare)
      setStep(2)
    } catch (error) {
      console.error('Failed to estimate fare:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmBooking = async () => {
    setLoading(true)
    try {
      const ride = await rideService.requestRide({
        pickup_latitude: pickupLocation.lat,
        pickup_longitude: pickupLocation.lng,
        pickup_address: pickupLocation.address,
        destination_latitude: dropoffLocation.lat,
        destination_longitude: dropoffLocation.lng,
        destination_address: dropoffLocation.address,
      })
      setCurrentRide(ride)
      navigate(`/ride/${ride.id}`)
    } catch (error) {
      console.error('Failed to book ride:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft size={20} />
          Back
        </button>

        <div className="bg-white rounded-2xl shadow-sm border p-8">
          <h1 className="text-2xl font-bold mb-6">Book a Ride</h1>

          {/* Step 1: Location Selection */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pickup Location
                </label>
                <LocationPicker
                  onLocationSelect={setPickupLocation}
                  placeholder="Enter pickup location"
                />
                {pickupLocation && (
                  <div className="mt-2 flex items-center gap-2 text-sm text-gray-600">
                    <MapPin size={16} className="text-primary-600" />
                    <span>{pickupLocation.address}</span>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dropoff Location
                </label>
                <LocationPicker
                  onLocationSelect={setDropoffLocation}
                  placeholder="Enter dropoff location"
                />
                {dropoffLocation && (
                  <div className="mt-2 flex items-center gap-2 text-sm text-gray-600">
                    <MapPin size={16} className="text-red-600" />
                    <span>{dropoffLocation.address}</span>
                  </div>
                )}
              </div>

              <Button
                onClick={handleEstimateFare}
                disabled={!pickupLocation || !dropoffLocation}
                loading={loading}
                className="w-full"
              >
                Get Fare Estimate
              </Button>
            </div>
          )}

          {/* Step 2: Confirmation */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <MapPin className="text-primary-600 mt-1" size={20} />
                  <div>
                    <p className="text-sm text-gray-500">Pickup</p>
                    <p className="font-medium">{pickupLocation.address}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <MapPin className="text-red-600 mt-1" size={20} />
                  <div>
                    <p className="text-sm text-gray-500">Dropoff</p>
                    <p className="font-medium">{dropoffLocation.address}</p>
                  </div>
                </div>
              </div>

              <div className="bg-primary-50 rounded-lg p-6 text-center">
                <p className="text-sm text-gray-600 mb-2">Estimated Fare</p>
                <p className="text-4xl font-bold text-primary-600">
                  {formatCurrency(estimatedFare)}
                </p>
                <p className="text-sm text-gray-500 mt-2">Final fare may vary</p>
              </div>

              <div className="flex gap-4">
                <Button
                  variant="outline"
                  onClick={() => setStep(1)}
                  className="flex-1"
                >
                  Change Locations
                </Button>
                <Button
                  onClick={handleConfirmBooking}
                  loading={loading}
                  className="flex-1"
                >
                  Confirm Booking
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}