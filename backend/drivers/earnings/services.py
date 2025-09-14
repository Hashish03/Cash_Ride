from django.db import transaction
from .models import DriverEarning, Payout
from drivers.models import DriverProfile
from rides.models import Ride
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

class EarningService:
    @staticmethod
    def record_earning(driver_profile, ride, amount, commission_rate=0.2):
        """
        Records a driver's earnings from a completed ride
        """
        try:
            with transaction.atomic():
                commission = amount * commission_rate
                net_earnings = amount - commission
                
                earning = DriverEarning.objects.create(
                    driver=driver_profile,
                    ride=ride,
                    amount=amount,
                    commission=commission,
                    net_earnings=net_earnings
                )
                
                # Update driver's total earnings
                driver_profile.total_earnings += net_earnings
                driver_profile.save()
                
                return earning
        except Exception as e:
            logger.error(f"Error recording earning: {str(e)}")
            raise

    @staticmethod
    def process_payout(driver_profile, amount, method):
        """
        Processes a payout request for a driver
        """
        try:
            with transaction.atomic():
                # Check available balance
                if amount > driver_profile.total_earnings - driver_profile.paid_earnings:
                    raise ValueError("Insufficient earnings for payout")
                
                # Create payout record
                payout = Payout.objects.create(
                    driver=driver_profile,
                    amount=amount,
                    method=method,
                    status='processing'
                )
                
                # In a real app, this would initiate an actual payout
                # For now, we'll just mark it as processed after a delay
                
                return payout
        except Exception as e:
            logger.error(f"Error processing payout: {str(e)}")
            raise