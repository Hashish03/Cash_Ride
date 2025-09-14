from .models import DriverProfile, Vehicle
from users.models import User
from django.db import transaction
import logging
from datetime import date
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class DriverService:
    @staticmethod
    def register_driver(data):
        """
        Registers a new driver with their vehicle information
        """
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    email=data['email'],
                    password=data['password'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    phone_number=data['phone_number'],
                    user_type='driver'
                )
                
                # Create driver profile
                driver_profile = DriverProfile.objects.create(user=user)
                
                # Create vehicle
                vehicle = Vehicle.objects.create(
                    driver=driver_profile,
                    make=data['make'],
                    model=data['model'],
                    year=data['year'],
                    color=data['color'],
                    vehicle_type=data['vehicle_type'],
                    license_plate=data['license_plate']
                )
                
                # Create availability record
                DriverAvailability.objects.create(driver=driver_profile)
                
                return driver_profile
        except Exception as e:
            logger.error(f"Driver registration failed: {str(e)}")
            raise

    @staticmethod
    def update_driver_status(driver_profile, online, available, location=None):
        """
        Updates driver's online/available status and location
        """
        try:
            with transaction.atomic():
                driver_profile.online = online
                driver_profile.available = available
                driver_profile.save()
                
                availability = driver_profile.availability
                availability.is_available = available
                if location:
                    availability.location = location
                availability.save()
                
                return driver_profile
        except Exception as e:
            logger.error(f"Error updating driver status: {str(e)}")
            raise

    @staticmethod
    def upload_document(driver_profile, document_data, file):
        """
        Uploads and validates a driver document
        """
        try:
            document = DriverDocument.objects.create(
                driver=driver_profile,
                document_type=document_data['document_type'],
                file=file,
                document_number=document_data.get('document_number'),
                expiry_date=document_data.get('expiry_date')
            )
            
            # In a real app, you might trigger document verification here
            return document
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise

    @staticmethod
    def verify_document(document_id, verified_by):
        """
        Marks a document as verified by admin
        """
        try:
            document = DriverDocument.objects.get(pk=document_id)
            document.is_verified = True
            document.verified_by = verified_by
            document.verified_at = date.today()
            document.save()
            
            # Check if all required documents are verified
            DriverService.check_driver_approval(document.driver)
            
            return document
        except Exception as e:
            logger.error(f"Error verifying document: {str(e)}")
            raise

    @staticmethod
    def check_driver_approval(driver_profile):
        """
        Checks if driver has all required documents verified
        and approves them if so
        """
        required_docs = ['license', 'registration', 'insurance']
        verified_docs = driver_profile.documents.filter(
            document_type__in=required_docs,
            is_verified=True
        ).values_list('document_type', flat=True).distinct()
        
        if set(required_docs).issubset(set(verified_docs)):
            driver_profile.status = 'approved'
            driver_profile.save()
            return True
        return False

    @staticmethod
    def record_earning(driver_profile, ride, amount, commission_rate=0.2):
        """
        Records a driver's earnings from a completed ride
        """
        try:
            commission = amount * commission_rate
            net_earnings = amount - commission
            
            earning = DriverEarning.objects.create(
                driver=driver_profile,
                ride=ride,
                amount=amount,
                commission=commission,
                net_earnings=net_earnings
            )
            
            # Update driver's total earnings and ride count
            driver_profile.total_earnings += net_earnings
            driver_profile.total_rides += 1
            driver_profile.save()
            
            return earning
        except Exception as e:
            logger.error(f"Error recording driver earning: {str(e)}")
            raise

    @staticmethod
    def update_driver_rating(driver_profile, ride, rating, feedback=None):
        """
        Updates driver's rating based on new feedback
        """
        try:
            # Create rating record
            DriverRating.objects.create(
                driver=driver_profile,
                ride=ride,
                rating=rating,
                feedback=feedback
            )
            
            # Recalculate average rating
            ratings = driver_profile.ratings.all()
            average_rating = sum(r.rating for r in ratings) / len(ratings)
            
            driver_profile.rating = round(average_rating, 2)
            driver_profile.save()
            
            return driver_profile
        except Exception as e:
            logger.error(f"Error updating driver rating: {str(e)}")
            raise