import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapPin, Clock, DollarSign, Plus } from 'lucide-react'
import Header from '../../components/layout/Header'
import Button from '../../components/common/Button'
import RideHistory from '../../components/ride/RideHistory'
import { useRideStore } from '../../store/rideStore'
import { useGeolocation } from '../../hooks/useGeolocation'

export default function PassengerHome() {
  const navigate = useNavigate()
  const { currentRide } = useRideStore()
  const { currentLocation } = useGeolocation()
  const [activeTab, setActiveTab] = useState('current')

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-2xl p-8 text-white mb-8">
          <h1 className="text-3xl font-bold mb-2">Where to?</h1>
          <p className="text-primary-100 mb-6">Book your ride in seconds</p>
          <Button
            onClick={() => navigate('/book-ride')}
            variant="secondary"
            size="lg"
            className="bg-white text-primary-600 hover:bg-gray-100"
          >
            <Plus size={20} />
            Book a Ride
          </Button>
        </div>

        {/* Current Ride */}
        {currentRide && (
          <div className="bg-white rounded-xl shadow-sm border p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Current Ride</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <MapPin className="text-primary-600" size={20} />
                <div>
                  <p className="text-sm text-gray-500">Pickup</p>
                  <p className="font-medium">{currentRide.pickup_address}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <MapPin className="text-red-600" size={20} />
                <div>
                  <p className="text-sm text-gray-500">Destination</p>
                  <p className="font-medium">{currentRide.destination_address}</p>
                </div>
              </div>
            </div>
            <Button 
              onClick={() => navigate(`/ride/${currentRide.id}`)}
              className="w-full mt-4"
            >
              Track Ride
            </Button>
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab('current')}
              className={`flex-1 px-6 py-4 font-medium transition-colors ${
                activeTab === 'current'
                  ? 'text-primary-600 border-b-2 border-primary-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Activity
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex-1 px-6 py-4 font-medium transition-colors ${
                activeTab === 'history'
                  ? 'text-primary-600 border-b-2 border-primary-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              History
            </button>
          </div>

          <div className="p-6">
            {activeTab === 'current' && (
              <div className="text-center py-12">
                <Clock className="mx-auto text-gray-400 mb-4" size={48} />
                <p className="text-gray-500">No recent activity</p>
              </div>
            )}
            {activeTab === 'history' && <RideHistory />}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
                <MapPin className="text-primary-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Trips</p>
                <p className="text-2xl font-bold">24</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <DollarSign className="text-green-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Spent</p>
                <p className="text-2xl font-bold">$486</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Clock className="text-blue-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-500">Avg Rating</p>
                <p className="text-2xl font-bold">4.8</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}