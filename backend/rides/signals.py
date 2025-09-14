from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Ride
from drivers.services import DriverService
from payments.services import PaymentService
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Ride)
def handle_ride_status_change(sender, instance, created, **kwargs):
    """
    Handle ride status changes and trigger appropriate actions
    """
    if not created:
        try:
            # When ride is completed, process payment and record earnings
            if instance.status == 'completed' and instance.payment is None:
                payment = PaymentService.process_ride_payment(instance)
                DriverService.record_earning(
                    instance.driver.driver_profile,
                    instance,
                    instance.total_fare
                )
                
            # When driver is assigned, notify rider
            elif instance.status == 'driver_assigned':
                from .notifications.services import notify_rider_driver_assigned
                notify_rider_driver_assigned(instance)
                
        except Exception as e:
            logger.error(f"Error handling ride status change: {str(e)}")

@receiver(pre_save, sender=Ride)
def validate_ride_status_change(sender, instance, **kwargs):
    """
    Validate ride status transitions
    """
    if instance.pk:
        original = Ride.objects.get(pk=instance.pk)
        if original.status != instance.status:
            valid_transitions = {
                'requested': ['driver_assigned', 'cancelled'],
                'driver_assigned': ['arrived', 'cancelled'],
                'arrived': ['in_progress', 'cancelled'],
                'in_progress': ['completed', 'cancelled'],
                'completed': [],
                'cancelled': []
            }
            
            if instance.status not in valid_transitions[original.status]:
                raise ValueError(f"Invalid status transition from {original.status} to {instance.status}")