import { useState, useEffect } from 'react'
import { DollarSign, MapPin, Clock, ToggleLeft, ToggleRight } from 'lucide-react'
import Header from '../../components/layout/Header'
import Card from '../../components/common/Card'
import Button from '../../components/common/Button'
import { useAuth } from '../../hooks/useAuth'

export function DriverDashboard() {
  const { user } = useAuth()
  const [isOnline, setIsOnline] = useState(false)
  const [todayEarnings, setTodayEarnings] = useState(0)
  const [todayTrips, setTodayTrips] = useState(0)

  const toggleOnlineStatus = () => {
    setIsOnline(!isOnline)
    // Update status via API
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Online Status Toggle */}
        <Card className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold mb-2">
                {isOnline ? "You're Online" : "You're Offline"}
              </h2>
              <p className="text-gray-600">
                {isOnline ? 'Ready to accept rides' : 'Toggle to start accepting rides'}
              </p>
            </div>
            <button
              onClick={toggleOnlineStatus}
              className={`relative inline-flex h-16 w-32 items-center rounded-full transition-colors ${
                isOnline ? 'bg-green-500' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-12 w-12 transform rounded-full bg-white shadow-lg transition-transform ${
                  isOnline ? 'translate-x-16' : 'translate-x-2'
                }`}
              />
              {isOnline ? (
                <ToggleRight className="absolute right-3 text-white" size={24} />
              ) : (
                <ToggleLeft className="absolute left-3 text-gray-500" size={24} />
              )}
            </button>
          </div>
        </Card>

        {/* Today's Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <DollarSign className="text-green-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Today's Earnings</p>
                <p className="text-2xl font-bold">${todayEarnings}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <MapPin className="text-blue-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Today's Trips</p>
                <p className="text-2xl font-bold">{todayTrips}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Clock className="text-purple-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Online Time</p>
                <p className="text-2xl font-bold">0h 0m</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Available Rides */}
        <Card>
          <h2 className="text-xl font-semibold mb-6">Available Rides</h2>
          {!isOnline ? (
            <div className="text-center py-12">
              <Clock className="mx-auto text-gray-400 mb-4" size={48} />
              <p className="text-gray-600">Go online to see available rides</p>
              <Button onClick={toggleOnlineStatus} className="mt-4">
                Go Online
              </Button>
            </div>
          ) : (
            <div className="text-center py-12">
              <MapPin className="mx-auto text-gray-400 mb-4" size={48} />
              <p className="text-gray-600">No rides available at the moment</p>
              <p className="text-sm text-gray-500 mt-2">We'll notify you when a ride request comes in</p>
            </div>
          )}
        </Card>

        {/* Recent Activity */}
        <Card className="mt-8">
          <h2 className="text-xl font-semibold mb-6">Recent Trips</h2>
          <div className="text-center py-12">
            <p className="text-gray-500">No recent trips</p>
          </div>
        </Card>
      </div>
    </div>
  )
}