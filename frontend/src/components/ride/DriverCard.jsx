import { Star, Car, Phone } from 'lucide-react'

export default function DriverCard({ driver }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center gap-4">
        {/* Driver Avatar */}
        <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center">
          <span className="text-2xl font-bold text-gray-600">
            {driver.first_name?.[0]}{driver.last_name?.[0]}
          </span>
        </div>

        {/* Driver Info */}
        <div className="flex-1">
          <h3 className="font-semibold text-lg">
            {driver.first_name} {driver.last_name}
          </h3>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Star size={16} className="text-yellow-500 fill-yellow-500" />
            <span>{driver.rating?.toFixed(1)} ({driver.total_trips} trips)</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-600 mt-1">
            <Car size={16} />
            <span>{driver.vehicle?.make} {driver.vehicle?.model}</span>
            <span className="text-gray-400">• {driver.vehicle?.color}</span>
          </div>
        </div>

        {/* Call Button */}
        <button className="p-3 bg-primary-100 text-primary-600 rounded-full hover:bg-primary-200">
          <Phone size={20} />
        </button>
      </div>

      {/* License Plate */}
      <div className="mt-4 pt-4 border-t">
        <div className="bg-gray-100 rounded-lg px-4 py-2 text-center">
          <span className="font-mono font-bold text-lg tracking-wider">
            {driver.vehicle?.license_plate}
          </span>
        </div>
      </div>
    </div>
  )
}