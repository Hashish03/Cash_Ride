from django.conf import settings
from math import radians, sin, cos, sqrt, atan2
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


# Base pricing configuration
PRICING_CONFIG = {
    'standard': {
        'base_fare': 2.50,
        'per_km': 1.50,
        'per_minute': 0.25,
        'minimum_fare': 5.00
    },
    'premium': {
        'base_fare': 5.00,
        'per_km': 2.50,
        'per_minute': 0.40,
        'minimum_fare': 10.00
    },
    'xl': {
        'base_fare': 4.00,
        'per_km': 2.00,
        'per_minute': 0.30,
        'minimum_fare': 8.00
    },
    'pet': {
        'base_fare': 3.00,
        'per_km': 1.75,
        'per_minute': 0.30,
        'minimum_fare': 7.00
    },
    'shared': {
        'base_fare': 1.50,
        'per_km': 1.00,
        'per_minute': 0.15,
        'minimum_fare': 3.50
    }
}

def haversine_distance(lat1, lon1, lat2, lon2) -> Decimal:
    """
    Calculate the great-circle distance between two points 
    on the Earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Radius of Earth in kilometers
    km = 6371 * c
    return km

def calculate_fare_estimate(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, 
                          ride_type, actual_distance=None, actual_duration=None,
                          surge_multiplier=1.0) -> Decimal:
    """
    Calculates fare estimate for a ride
    
    Args:
        pickup_lat: Pickup location latitude
        pickup_lon: Pickup location longitude
        dropoff_lat: Dropoff location latitude (None if not specified)
        dropoff_lon: Dropoff location longitude (None if not specified)
        ride_type: Type of ride (standard, premium, etc.)
        actual_distance: Actual distance in meters (optional)
        actual_duration: Actual duration in seconds (optional)
        surge_multiplier: Surge pricing multiplier (default 1.0)
    """
    config = PRICING_CONFIG.get(ride_type, PRICING_CONFIG['standard'])
    
    # Calculate distance if not provided
    if actual_distance is None and dropoff_lat is not None and dropoff_lon is not None:
        distance_km = haversine_distance(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    elif actual_distance is not None:
        distance_km = actual_distance / 1000  # Convert meters to km
    else:
        distance_km = 0
    
    # Calculate duration estimate if not provided (assuming 30 km/h average speed)
    if actual_duration is None and distance_km > 0:
        duration_minutes = (distance_km / 30) * 60
    elif actual_duration is not None:
        duration_minutes = actual_duration / 60  # Convert seconds to minutes
    else:
        duration_minutes = 0
    
    # Calculate fare components
    base_fare = config['base_fare']
    distance_fare = distance_km * config['per_km']
    time_fare = duration_minutes * config['per_minute']
    
    # Calculate total fare with surge pricing
    total_fare = (base_fare + distance_fare + time_fare) * surge_multiplier
    
    # Ensure minimum fare
    total_fare = max(total_fare, config['minimum_fare'])
    
    return {
        'base_fare': base_fare,
        'distance_fare': distance_fare,
        'time_fare': time_fare,
        'surge_multiplier': surge_multiplier,
        'total_fare': round(total_fare, 2),
        'estimated_distance': distance_km * 1000,  # km to meters
        'estimated_duration': duration_minutes * 60,  # minutes to seconds
    }