# backend/utils/location.py
import requests
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
import logging

logger = logging.getLogger(__name__)

class LocationService:
    """
    Location-based services for the ride-sharing app
    """
    
    def __init__(self):
        self.geocoding_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    
    def geocode_address(self, address):
        """Convert address to coordinates"""
        if not self.geocoding_api_key:
            return None
        
        try:
            url = 'https://maps.googleapis.com/maps/api/geocode/json'
            params = {
                'address': address,
                'key': self.geocoding_api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                return Point(location['lng'], location['lat'])
            
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")
        
        return None
    
    def reverse_geocode(self, latitude, longitude):
        """Convert coordinates to address"""
        if not self.geocoding_api_key:
            return None
        
        try:
            url = 'https://maps.googleapis.com/maps/api/geocode/json'
            params = {
                'latlng': f'{latitude},{longitude}',
                'key': self.geocoding_api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                return data['results'][0]['formatted_address']
            
        except Exception as e:
            logger.error(f"Reverse geocoding error: {str(e)}")
        
        return None
    
    def calculate_distance(self, point1, point2):
        """Calculate distance between two points"""
        try:
            distance = point1.distance(point2) * 111320  # Convert to meters
            return distance
        except Exception as e:
            logger.error(f"Distance calculation error: {str(e)}")
            return None
    
    def find_nearby_drivers(self, pickup_location, radius_km=5):
        """Find drivers within specified radius"""
        from rides.models import Driver  # Assuming you have a Driver model
        
        try:
            # Create a circle around the pickup location
            search_area = pickup_location.buffer(radius_km / 111.32)  # Convert km to degrees
            
            # Find active drivers in the area
            nearby_drivers = Driver.objects.filter(
                is_active=True,
                current_location__within=search_area
            ).order_by('?')  # Random order
            
            return nearby_drivers
            
        except Exception as e:
            logger.error(f"Driver search error: {str(e)}")
            return []