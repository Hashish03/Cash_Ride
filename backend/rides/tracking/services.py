from rides.models import RideLocationUpdate
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class TrackingService:
    @staticmethod
    def update_ride_location(ride, latitude: float, longitude: float, is_driver: bool):
        """
        Update ride location and broadcast to connected clients
        
        Args:
            ride: Ride instance
            latitude: Location latitude in decimal degrees
            longitude: Location longitude in decimal degrees
            is_driver: Whether this is a driver location update
        """
        try:
            # Validate coordinates
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                raise ValidationError("Invalid coordinates")
            
            # Save location update
            update = RideLocationUpdate.objects.create(
                ride=ride,
                latitude=latitude,
                longitude=longitude,
                is_driver_location=is_driver
            )
            
            # Broadcast via WebSocket
            channel_layer = get_channel_layer()
            group_name = f"ride_{ride.id}_tracking"
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "location.update",
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "is_driver": is_driver,
                        "timestamp": update.timestamp.isoformat()
                    }
                }
            )
            
            return update
        except Exception as e:
            logger.error(f"Error updating ride location: {str(e)}")
            raise

    @staticmethod
    def get_ride_route(ride):
        """
        Get the complete route for a ride with all location updates
        
        Returns:
            Dictionary containing:
            - pickup: {latitude, longitude}
            - dropoff: {latitude, longitude} or None
            - updates: List of location updates
        """
        updates = RideLocationUpdate.objects.filter(ride=ride).order_by('timestamp')
        return {
            "pickup": {
                "latitude": ride.pickup_latitude,
                "longitude": ride.pickup_longitude
            },
            "dropoff": {
                "latitude": ride.dropoff_latitude if ride.dropoff_latitude else None,
                "longitude": ride.dropoff_longitude if ride.dropoff_longitude else None
            },
            "updates": [
                {
                    "latitude": u.latitude,
                    "longitude": u.longitude,
                    "timestamp": u.timestamp.isoformat(),
                    "is_driver": u.is_driver_location
                } for u in updates
            ]
        }

    @staticmethod
    def get_latest_driver_location(ride_id):
        """
        Get the latest driver location for a ride
        
        Args:
            ride_id: ID of the ride
        Returns:
            Dictionary with latitude, longitude and timestamp or None
        """
        try:
            update = RideLocationUpdate.objects.filter(
                ride_id=ride_id,
                is_driver_location=True
            ).latest('timestamp')
            
            return {
                'latitude': update.latitude,
                'longitude': update.longitude,
                'timestamp': update.timestamp.isoformat()
            }
        except RideLocationUpdate.DoesNotExist:
            return None