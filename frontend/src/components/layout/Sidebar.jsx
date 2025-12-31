import { Loader2 } from 'lucide-react'

export default function Spinner({ size = 24, className = '' }) {
  return (
    <div className="flex items-center justify-center p-4">
      <Loader2 className={`animate-spin text-primary-600 ${className}`} size={size} />
    </div>
  )
}