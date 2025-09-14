# rides/utils.py
import math
from geopy.distance import geodesic

def calculate_fare(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng, vehicle_type):
    # Calculate distance in kilometers
    pickup = (pickup_lat, pickup_lng)
    dropoff = (dropoff_lat, dropoff_lng)
    distance = geodesic(pickup, dropoff).kilometers
    
    # Base fare and rates per vehicle type
    rates = {
        'standard': {'base': 2.50, 'per_km': 1.20, 'per_minute': 0.30},
        'premium': {'base': 5.00, 'per_km': 2.00, 'per_minute': 0.50},
        'xl': {'base': 3.50, 'per_km': 1.50, 'per_minute': 0.40}
    }
    
    # Estimate time (assuming average speed of 30km/h in city)
    estimated_time = (distance / 30) * 60  # in minutes
    
    # Calculate fare
    rate = rates.get(vehicle_type, rates['standard'])
    fare = rate['base'] + (distance * rate['per_km']) + (estimated_time * rate['per_minute'])
    
    # Apply minimum fare
    minimum_fare = max(5.0, rate['base'] * 2)
    fare = max(fare, minimum_fare)
    
    return round(fare, 2)