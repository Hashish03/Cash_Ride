from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import User
from .models import DriverProfile, DriverAvailability

@receiver(post_save, sender=User)
def create_driver_profile(sender, instance, created, **kwargs):
    """Automatically create driver profile when user is created as driver"""
    if created and instance.user_type == 'driver':
        DriverProfile.objects.create(user=instance)
        DriverAvailability.objects.create(driver=instance.driver_profile)

@receiver(post_save, sender=DriverProfile)
def update_driver_availability(sender, instance, created, **kwargs):
    """Update availability when driver profile changes"""
    if not created:
        availability, _ = DriverAvailability.objects.get_or_create(driver=instance)
        availability.is_available = instance.available
        availability.save()