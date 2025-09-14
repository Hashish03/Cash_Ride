from rides.models import DriverLocation, RideRequestLog
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def find_best_driver_match(ride, available_drivers):
    """
    Implements driver matching algorithm considering:
    - Proximity to pickup location
    - Driver rating
    - Driver acceptance rate
    - Ride type compatibility
    """
    try:
        # Filter drivers who have rejected this ride recently
        recent_rejections = RideRequestLog.objects.filter(
            ride=ride,
            status='rejected',
            timestamp__gte=datetime.now() - timedelta(minutes=5)
        ).values_list('driver_id', flat=True)
        
        available_drivers = available_drivers.exclude(
            driver_id__in=recent_rejections
        )
        
        if not available_drivers:
            return None
        
        # Simple matching: closest driver first
        # In a real app, this would be more sophisticated
        best_driver = available_drivers.first()
        
        return best_driver
    except Exception as e:
        logger.error(f"Error in driver matching: {str(e)}")
        return None

def calculate_driver_score(driver, ride):
    """
    Calculates a score for driver matching
    """
    score = 0
    
    # Distance score (closer is better)
    distance_km = driver.distance.km
    score += max(0, 100 - (distance_km * 10))  # 0-100 based on distance
    
    # Rating score (higher is better)
    if hasattr(driver.driver, 'driver_profile'):
        score += driver.driver.driver_profile.rating * 20  # Assuming 1-5 rating
        
    # Acceptance rate (higher is better)
    # Would query historical acceptance rate
    
    # Compatibility with ride type
    # Would check if driver's vehicle matches ride type
    
    return score