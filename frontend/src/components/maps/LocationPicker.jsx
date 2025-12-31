import { useState, useEffect } from 'react'
import { MapPin, Search } from 'lucide-react'
import Input from '../common/Input'
import { debounce } from '../../utils/helpers'

export default function LocationPicker({ onLocationSelect, placeholder }) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(false)

  const searchLocations = debounce(async (searchQuery) => {
    if (!searchQuery) {
      setSuggestions([])
      return
    }

    setLoading(true)
    try {
      // Use Google Places Autocomplete API
      const service = new window.google.maps.places.AutocompleteService()
      service.getPlacePredictions(
        { input: searchQuery },
        (predictions, status) => {
          if (status === window.google.maps.places.PlacesServiceStatus.OK) {
            setSuggestions(predictions)
          }
          setLoading(false)
        }
      )
    } catch (error) {
      console.error('Location search error:', error)
      setLoading(false)
    }
  }, 500)

  useEffect(() => {
    searchLocations(query)
  }, [query])

  const handleSelectLocation = async (place) => {
    const geocoder = new window.google.maps.Geocoder()
    geocoder.geocode({ placeId: place.place_id }, (results, status) => {
      if (status === 'OK' && results[0]) {
        const location = results[0].geometry.location
        onLocationSelect({
          address: place.description,
          lat: location.lat(),
          lng: location.lng(),
        })
        setQuery(place.description)
        setSuggestions([])
      }
    })
  }

  return (
    <div className="relative">
      <Input
        icon={Search}
        placeholder={placeholder || 'Search location...'}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {suggestions.length > 0 && (
        <div className="absolute z-10 w-full mt-2 bg-white rounded-lg shadow-lg border max-h-60 overflow-y-auto">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion.place_id}
              onClick={() => handleSelectLocation(suggestion)}
              className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-start gap-3 border-b last:border-b-0"
            >
              <MapPin size={18} className="text-gray-400 mt-1 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {suggestion.structured_formatting.main_text}
                </p>
                <p className="text-xs text-gray-500">
                  {suggestion.structured_formatting.secondary_text}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}