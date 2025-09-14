from django.contrib.gis.db.models.functions import Distance
from drivers.models import DriverProfile
import logging
from typing import List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

class MatchingStrategy:
    """
    Base class for driver matching strategies
    """
    def find_best_driver(self, ride, available_drivers):
        raise NotImplementedError

class ProximityFirstStrategy(MatchingStrategy):
    """
    Matches the closest available driver
    """
    def find_best_driver(self, ride, available_drivers):
        return available_drivers.annotate(
            distance=Distance('location', ride.pickup_location)
        ).order_by('distance').first()

class RatingFirstStrategy(MatchingStrategy):
    """
    Matches the highest rated available driver within radius
    """
    def find_best_driver(self, ride, available_drivers):
        return available_drivers.annotate(
            distance=Distance('location', ride.pickup_location)
        ).filter(
            distance__lte=10000  # 10km radius
        ).order_by('-driver__driver_profile__rating', 'distance').first()

class HybridStrategy(MatchingStrategy):
    """
    Combines proximity and rating with some business logic
    """
    def __init__(self, rating_weight=0.7, proximity_weight=0.3):
        self.rating_weight = Decimal(rating_weight)
        self.proximity_weight = Decimal(proximity_weight)
    
    def find_best_driver(self, ride, available_drivers):
        drivers = available_drivers.annotate(
            distance=Distance('location', ride.pickup_location)
        ).filter(
            distance__lte=15000  # 15km max distance
        )
        
        if not drivers:
            return None
            
        # Normalize ratings and distances to 0-1 scale
        max_rating = max(d.driver.driver_profile.rating for d in drivers)
        min_distance = min(d.distance.km for d in drivers)
        max_distance = max(d.distance.km for d in drivers)
        
        # Calculate score for each driver
        best_driver = None
        best_score = Decimal('-Infinity')
        
        for driver in drivers:
            if max_rating > 0:
                normalized_rating = Decimal(driver.driver.driver_profile.rating) / Decimal(max_rating)
            else:
                normalized_rating = Decimal('0')
                
            if max_distance > 0:
                normalized_distance = 1 - (Decimal(driver.distance.km) - Decimal(min_distance)) / Decimal(max_distance - min_distance)
            else:
                normalized_distance = Decimal('1')
                
            score = (normalized_rating * self.rating_weight + 
                    normalized_distance * self.proximity_weight)
            
            if score > best_score:
                best_score = score
                best_driver = driver
                
        return best_driver