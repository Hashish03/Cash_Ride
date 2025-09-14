from .models import Ride, RideLocationUpdate, DriverLocation, RideRequestLog, CancellationReason
from django.db import transaction
from users.models import User
import logging
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from .utils.pricing import calculate_fare_estimate
from .matching.algorithms import find_best_driver_match
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class RideService:
    @staticmethod
    def create_ride_request(rider, data):
        """
        Creates a new ride request
        
        Args:
            rider: User instance making the request
            data: Dictionary containing:
                - pickup_latitude: float
                - pickup_longitude: float
                - pickup_address: str
                - dropoff_latitude: float (optional)
                - dropoff_longitude: float (optional)
                - dropoff_address: str (optional)
                - ride_type: str
        """
        try:
            with transaction.atomic():
                # Calculate fare estimate
                fare_estimate = calculate_fare_estimate(
                    pickup_lat=data['pickup_latitude'],
                    pickup_lon=data['pickup_longitude'],
                    dropoff_lat=data.get('dropoff_latitude'),
                    dropoff_lon=data.get('dropoff_longitude'),
                    ride_type=data['ride_type']
                )
                
                # Create ride
                ride = Ride.objects.create(
                    rider=rider,
                    pickup_latitude=data['pickup_latitude'],
                    pickup_longitude=data['pickup_longitude'],
                    pickup_address=data['pickup_address'],
                    dropoff_latitude=data.get('dropoff_latitude'),
                    dropoff_longitude=data.get('dropoff_longitude'),
                    dropoff_address=data.get('dropoff_address'),
                    ride_type=data['ride_type'],
                    status='requested',
                    **fare_estimate
                )
                
                # Find and assign driver
                assigned = RideService.assign_driver_to_ride(ride)
                if not assigned:
                    ride.status = 'cancelled'
                    ride.save()
                    RideService.create_cancellation_reason(
                        ride, 
                        'system', 
                        'No available drivers found'
                    )
                    return None
                
                return ride
        except Exception as e:
            logger.error(f"Error creating ride request: {str(e)}")
            raise

    @staticmethod
    def assign_driver_to_ride(ride):
        """
        Finds and assigns the best available driver for a ride
        
        Args:
            ride: Ride instance needing a driver
        Returns:
            bool: True if driver assigned, False otherwise
        """
        try:
            # Get available drivers near pickup location
            available_drivers = DriverLocation.objects.filter(
                is_available=True
            )
            
            # Filter drivers within 10km radius using Haversine formula
            nearby_drivers = []
            for driver_loc in available_drivers:
                distance = RideService.calculate_distance(
                    ride.pickup_latitude, ride.pickup_longitude,
                    driver_loc.latitude, driver_loc.longitude
                )
                if distance <= 10:  # 10km radius
                    driver_loc.distance = distance
                    nearby_drivers.append(driver_loc)
            
            # Sort by distance and take top 20 closest
            nearby_drivers = sorted(nearby_drivers, key=lambda x: x.distance)[:20]
            
            if not nearby_drivers:
                return False
            
            # Find best match using matching algorithm
            best_driver = find_best_driver_match(ride, nearby_drivers)
            
            if not best_driver:
                return False
            
            # Assign driver to ride
            ride.driver = best_driver.driver
            ride.status = 'driver_assigned'
            ride.save()
            
            # Create request log
            RideRequestLog.objects.create(
                ride=ride,
                driver=best_driver.driver,
                status='sent'
            )
            
            # Mark driver as unavailable
            best_driver.is_available = False
            best_driver.save()
            
            return True
        except Exception as e:
            logger.error(f"Error assigning driver to ride: {str(e)}")
            return False

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """
        Calculate distance between two points in kilometers using Haversine formula
        """
        # Convert decimal degrees to radians 
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        
        # Haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a)) 
        return 6371 * c  # Radius of earth in kilometers

    @staticmethod
    def update_ride_status(ride, new_status, current_lat=None, current_lon=None):
        """
        Updates ride status with appropriate timestamps
        
        Args:
            ride: Ride instance to update
            new_status: New status value
            current_lat: Current latitude (optional)
            current_lon: Current longitude (optional)
        """
        try:
            with transaction.atomic():
                status_updates = {
                    'accepted': {'field': 'accepted_at'},
                    'arrived': {'field': 'arrived_at'},
                    'in_progress': {'field': 'started_at'},
                    'completed': {'field': 'completed_at'},
                }
                
                if new_status in status_updates:
                    setattr(ride, status_updates[new_status]['field'], timezone.now())
                
                ride.status = new_status
                ride.save()
                
                if current_lat is not None and current_lon is not None:
                    RideService.update_ride_location(
                        ride, 
                        current_lat, 
                        current_lon, 
                        is_driver=True
                    )
                
                return ride
        except Exception as e:
            logger.error(f"Error updating ride status: {str(e)}")
            raise

    @staticmethod
    def update_ride_location(ride, latitude, longitude, is_driver=True):
        """
        Records a location update for a ride
        
        Args:
            ride: Ride instance
            latitude: Location latitude
            longitude: Location longitude
            is_driver: Whether this is a driver location update
        """
        try:
            # Validate coordinates
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                raise ValidationError("Invalid coordinates")
            
            RideLocationUpdate.objects.create(
                ride=ride,
                latitude=latitude,
                longitude=longitude,
                is_driver_location=is_driver
            )
            
            # If this is a driver update, also update their current location
            if is_driver and ride.driver:
                DriverLocation.objects.update_or_create(
                    driver=ride.driver,
                    defaults={
                        'latitude': latitude,
                        'longitude': longitude
                    }
                )
        except Exception as e:
            logger.error(f"Error updating ride location: {str(e)}")
            raise

    @staticmethod
    def complete_ride(ride, actual_distance, actual_duration):
        """
        Completes a ride and processes payment
        
        Args:
            ride: Ride instance to complete
            actual_distance: Actual distance traveled in meters
            actual_duration: Actual duration in seconds
        """
        try:
            with transaction.atomic():
                # Calculate final fare based on actual distance/duration
                final_fare = calculate_fare_estimate(
                    pickup_lat=ride.pickup_latitude,
                    pickup_lon=ride.pickup_longitude,
                    dropoff_lat=ride.dropoff_latitude,
                    dropoff_lon=ride.dropoff_longitude,
                    ride_type=ride.ride_type,
                    actual_distance=actual_distance,
                    actual_duration=actual_duration,
                    surge_multiplier=ride.surge_multiplier
                )
                
                # Update ride with actual metrics and fare
                ride.actual_distance = actual_distance
                ride.actual_duration = actual_duration
                ride.total_fare = final_fare['total_fare']
                ride.status = 'completed'
                ride.completed_at = timezone.now()
                ride.save()
                
                # Mark driver as available again
                if ride.driver:
                    DriverLocation.objects.filter(driver=ride.driver).update(is_available=True)
                
                return ride
        except Exception as e:
            logger.error(f"Error completing ride: {str(e)}")
            raise

    @staticmethod
    def cancel_ride(ride, cancelled_by, reason=None):
        """
        Cancels a ride with a reason
        
        Args:
            ride: Ride instance to cancel
            cancelled_by: Who cancelled ('rider', 'driver', or 'system')
            reason: Optional cancellation reason
        """
        try:
            with transaction.atomic():
                ride.status = 'cancelled'
                ride.cancelled_at = timezone.now()
                ride.save()
                
                RideService.create_cancellation_reason(ride, cancelled_by, reason)
                
                # If driver was assigned, mark them as available again
                if ride.driver and ride.status != 'completed':
                    DriverLocation.objects.filter(driver=ride.driver).update(is_available=True)
                
                return ride
        except Exception as e:
            logger.error(f"Error cancelling ride: {str(e)}")
            raise

    @staticmethod
    def create_cancellation_reason(ride, cancelled_by, reason):
        """
        Creates a cancellation reason record
        """
        try:
            return CancellationReason.objects.create(
                ride=ride,
                cancelled_by=cancelled_by,
                reason=reason or "No reason provided"
            )
        except Exception as e:
            logger.error(f"Error creating cancellation reason: {str(e)}")
            raise

    @staticmethod
    def rate_ride(ride, rating_type, rating_value, feedback=None):
        """
        Records a rating for a ride (either rider or driver)
        
        Args:
            ride: Ride instance to rate
            rating_type: 'rider' or 'driver'
            rating_value: Numeric rating value
            feedback: Optional text feedback
        """
        try:
            if rating_type == 'rider':
                ride.rider_rating = rating_value
            elif rating_type == 'driver':
                ride.driver_rating = rating_value
            
            if feedback:
                ride.notes = feedback
            
            ride.save()
            return ride
        except Exception as e:
            logger.error(f"Error rating ride: {str(e)}")
            raise