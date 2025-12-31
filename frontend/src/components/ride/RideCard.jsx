import { MapPin, Clock, DollarSign } from 'lucide-react'
import { formatCurrency, formatDate, formatTime } from '../../utils/helpers'
import { RIDE_STATUS } from '../../utils/constants'

export default function RideCard({ ride, onClick }) {
  const statusColors = {
    [RIDE_STATUS.COMPLETED]: 'bg-green-100 text-green-800',
    [RIDE_STATUS.CANCELLED]: 'bg-red-100 text-red-800',
    [RIDE_STATUS.IN_PROGRESS]: 'bg-blue-100 text-blue-800',
    [RIDE_STATUS.REQUESTED]: 'bg-yellow-100 text-yellow-800',
  }

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <MapPin size={16} className="text-primary-600" />
            <span className="text-sm font-medium">{ride.pickup_address}</span>
          </div>
          <div className="flex items-center gap-2">
            <MapPin size={16} className="text-red-600" />
            <span className="text-sm text-gray-600">{ride.destination_address}</span>
          </div>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[ride.status]}`}>
          {ride.status}
        </span>
      </div>

      <div className="flex items-center justify-between text-sm text-gray-600">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <Clock size={16} />
            <span>{formatDate(ride.requested_at)}</span>
          </div>
          <div className="flex items-center gap-1">
            <DollarSign size={16} />
            <span className="font-semibold">{formatCurrency(ride.fare_amount)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}