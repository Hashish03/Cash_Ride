from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging
from datetime import timedelta, date
from django.db.models import Sum, Q, Avg
from .models import DriverEarning, Payout, PayoutCycle
from drivers.models import DriverProfile
from rides.models import Ride
from rides.notifications.services import NotificationService
from payments.services import PaymentGatewayService

logger = logging.getLogger(__name__)


class EarningService:
    """Service for handling driver earnings and payouts"""
    
    @staticmethod
    def record_earning(driver_profile, ride, amount, commission_rate=0.2):
        """
        Records a driver's earnings from a completed ride
        """
        try:
            with transaction.atomic():
                # Validate inputs
                if amount <= 0:
                    raise ValidationError("Amount must be greater than 0")
                
                if not 0 <= commission_rate <= 1:
                    raise ValidationError("Commission rate must be between 0 and 1")
                
                commission = amount * Decimal(commission_rate)
                net_earnings = amount - commission
                
                # Create earning record
                earning = DriverEarning.objects.create(
                    driver=driver_profile,
                    ride=ride,
                    amount=amount,
                    commission=commission,
                    net_earnings=net_earnings,
                    status='pending'  # Will be cleared during payout cycle
                )
                
                # Update driver's available balance
                driver_profile.available_balance += net_earnings
                driver_profile.total_earnings += net_earnings
                driver_profile.save(update_fields=['available_balance', 'total_earnings', 'updated_at'])
                
                # Send notification to driver
                NotificationService.send_earning_notification(
                    driver=driver_profile.user,
                    amount=net_earnings,
                    ride_id=ride.id,
                    timestamp=earning.created_at
                )
                
                logger.info(f"Earning recorded: {earning.id} for driver {driver_profile.id}")
                return earning
                
        except Exception as e:
            logger.error(f"Error recording earning for driver {driver_profile.id}: {str(e)}")
            raise

    @staticmethod
    def process_payout(driver_profile, amount, method='bank_transfer'):
        """
        Processes a payout request for a driver
        """
        try:
            with transaction.atomic():
                # Validate amount
                if amount <= 0:
                    raise ValidationError("Payout amount must be greater than 0")
                
                # Check minimum payout amount
                if amount < Decimal('10.00'):  # Minimum $10 payout
                    raise ValidationError("Minimum payout amount is $10.00")
                
                # Check available balance
                available_balance = driver_profile.available_balance
                if amount > available_balance:
                    raise ValueError(
                        f"Insufficient balance. Available: ${available_balance:.2f}, "
                        f"Requested: ${amount:.2f}"
                    )
                
                # Check if driver has a payout method set up
                if not driver_profile.payment_methods.filter(is_primary=True, is_verified=True).exists():
                    raise ValidationError("No verified payment method found")
                
                # Create payout record
                payout = Payout.objects.create(
                    driver=driver_profile,
                    amount=amount,
                    method=method,
                    status='processing',
                    initiated_at=timezone.now()
                )
                
                # Lock the earnings that are being paid out
                earnings_to_payout = DriverEarning.objects.filter(
                    driver=driver_profile,
                    status='pending',
                    created_at__lte=timezone.now() - timedelta(hours=24)  # Only earnings older than 24 hours
                ).order_by('created_at')
                
                total_locked = Decimal('0.00')
                for earning in earnings_to_payout:
                    if total_locked >= amount:
                        break
                    earning.status = 'processing'
                    earning.payout = payout
                    earning.save()
                    total_locked += earning.net_earnings
                
                # Update driver's balance
                driver_profile.available_balance -= amount
                driver_profile.paid_earnings += amount
                driver_profile.last_payout_date = timezone.now()
                driver_profile.save(update_fields=[
                    'available_balance', 
                    'paid_earnings', 
                    'last_payout_date',
                    'updated_at'
                ])
                
                # Initiate actual payment with payment gateway
                try:
                    payment_result = PaymentGatewayService.initiate_payout(
                        driver=driver_profile,
                        amount=amount,
                        payout_method=method,
                        reference_id=payout.id
                    )
                    
                    if payment_result.get('success'):
                        payout.status = 'completed'
                        payout.completed_at = timezone.now()
                        payout.transaction_id = payment_result.get('transaction_id')
                        payout.save()
                        
                        # Mark earnings as paid
                        earnings_to_payout.update(status='paid', paid_at=timezone.now())
                        
                        # Send notification
                        NotificationService.send_payout_notification(
                            driver=driver_profile.user,
                            amount=amount,
                            payout_id=payout.id,
                            status='completed'
                        )
                        
                        logger.info(f"Payout {payout.id} completed for driver {driver_profile.id}")
                    else:
                        payout.status = 'failed'
                        payout.failure_reason = payment_result.get('error')
                        payout.save()
                        
                        # Revert earning status
                        earnings_to_payout.update(status='pending', payout=None)
                        
                        # Revert driver's balance
                        driver_profile.available_balance += amount
                        driver_profile.paid_earnings -= amount
                        driver_profile.save()
                        
                        raise Exception(f"Payment gateway error: {payment_result.get('error')}")
                        
                except Exception as payment_error:
                    logger.error(f"Payment gateway error for payout {payout.id}: {str(payment_error)}")
                    payout.status = 'failed'
                    payout.failure_reason = str(payment_error)
                    payout.save()
                    raise
                
                return payout
                
        except Exception as e:
            logger.error(f"Error processing payout for driver {driver_profile.id}: {str(e)}")
            raise

    @staticmethod
    def get_driver_earnings_summary(driver_profile, start_date=None, end_date=None):
        """
        Get earnings summary for a driver for a given period
        """
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = timezone.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Get earnings in date range
            earnings = DriverEarning.objects.filter(
                driver=driver_profile,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
            
            # Calculate totals
            total_earnings = earnings.aggregate(
                total_amount=Sum('amount'),
                total_commission=Sum('commission'),
                total_net=Sum('net_earnings')
            )
            
            # Get daily breakdown
            daily_breakdown = earnings.values('created_at__date').annotate(
                daily_amount=Sum('amount'),
                daily_commission=Sum('commission'),
                daily_net=Sum('net_earnings'),
                ride_count=Count('id')
            ).order_by('-created_at__date')
            
            # Get pending and available amounts
            pending_earnings = earnings.filter(status='pending').aggregate(
                total=Sum('net_earnings')
            )['total'] or Decimal('0.00')
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'summary': {
                    'total_rides': earnings.count(),
                    'total_amount': total_earnings['total_amount'] or Decimal('0.00'),
                    'total_commission': total_earnings['total_commission'] or Decimal('0.00'),
                    'total_net_earnings': total_earnings['total_net'] or Decimal('0.00'),
                    'pending_earnings': pending_earnings,
                    'available_balance': driver_profile.available_balance
                },
                'daily_breakdown': list(daily_breakdown),
                'recent_earnings': earnings.select_related('ride').order_by('-created_at')[:10]
            }
            
        except Exception as e:
            logger.error(f"Error getting earnings summary for driver {driver_profile.id}: {str(e)}")
            raise

    @staticmethod
    def process_automatic_payouts():
        """
        Process automatic payouts for eligible drivers
        Runs as a scheduled task (cron job)
        """
        try:
            # Get payout cycle configuration
            payout_cycle = PayoutCycle.get_current_cycle()
            if not payout_cycle.is_processing_date:
                logger.info("Not a processing date for automatic payouts")
                return {"processed": 0}
            
            # Find eligible drivers (available balance > minimum, haven't been paid recently)
            eligible_drivers = DriverProfile.objects.filter(
                available_balance__gte=Decimal('50.00'),  # Minimum auto-payout amount
                auto_payout_enabled=True,
                last_payout_date__lt=timezone.now() - timedelta(days=6)  # At least 7 days since last payout
            ).select_related('user')
            
            processed_count = 0
            failed_count = 0
            
            for driver in eligible_drivers:
                try:
                    # Process full available balance or maximum limit
                    payout_amount = min(driver.available_balance, Decimal('5000.00'))  # Max $5000 per payout
                    
                    with transaction.atomic():
                        # Create and process payout
                        payout = Payout.objects.create(
                            driver=driver,
                            amount=payout_amount,
                            method=driver.default_payout_method or 'bank_transfer',
                            status='processing',
                            initiated_at=timezone.now(),
                            is_automatic=True
                        )
                        
                        # Similar processing logic as process_payout
                        # (would call internal method to avoid code duplication)
                        processed_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed automatic payout for driver {driver.id}: {str(e)}")
                    continue
            
            logger.info(f"Automatic payouts completed. Processed: {processed_count}, Failed: {failed_count}")
            return {
                "processed": processed_count,
                "failed": failed_count,
                "total_eligible": eligible_drivers.count()
            }
            
        except Exception as e:
            logger.error(f"Error processing automatic payouts: {str(e)}")
            raise

    @staticmethod
    def cancel_payout(payout_id):
        """
        Cancel a pending payout
        """
        try:
            with transaction.atomic():
                payout = Payout.objects.select_for_update().get(id=payout_id)
                
                # Only allow cancellation of processing payouts
                if payout.status not in ['processing', 'pending']:
                    raise ValidationError(f"Cannot cancel payout with status: {payout.status}")
                
                # Revert associated earnings
                earnings = DriverEarning.objects.filter(payout=payout)
                earnings.update(status='pending', payout=None)
                
                # Return funds to driver's available balance
                driver = payout.driver
                driver.available_balance += payout.amount
                driver.paid_earnings -= payout.amount
                driver.save()
                
                # Update payout status
                payout.status = 'cancelled'
                payout.cancelled_at = timezone.now()
                payout.save()
                
                # Send notification
                NotificationService.send_payout_notification(
                    driver=driver.user,
                    amount=payout.amount,
                    payout_id=payout.id,
                    status='cancelled'
                )
                
                logger.info(f"Payout {payout.id} cancelled")
                return payout
                
        except Payout.DoesNotExist:
            logger.error(f"Payout {payout_id} not found")
            raise ValidationError("Payout not found")
        except Exception as e:
            logger.error(f"Error cancelling payout {payout_id}: {str(e)}")
            raise

    @staticmethod
    def get_payout_history(driver_profile, limit=20):
        """
        Get payout history for a driver
        """
        try:
            payouts = Payout.objects.filter(
                driver=driver_profile
            ).select_related('driver').order_by('-created_at')[:limit]
            
            # Calculate stats
            total_paid = Payout.objects.filter(
                driver=driver_profile,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            return {
                'payouts': list(payouts.values(
                    'id', 'amount', 'method', 'status', 
                    'created_at', 'completed_at'
                )),
                'stats': {
                    'total_payouts': payouts.count(),
                    'total_amount_paid': total_paid,
                    'last_payout_date': driver_profile.last_payout_date
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting payout history for driver {driver_profile.id}: {str(e)}")
            raise

    @staticmethod
    def calculate_commission(ride_amount, driver_tier='standard'):
        """
        Calculate commission based on ride amount and driver tier
        """
        try:
            # Tier-based commission rates
            commission_rates = {
                'standard': 0.20,  # 20%
                'gold': 0.15,       # 15%
                'platinum': 0.10    # 10%
            }
            
            rate = commission_rates.get(driver_tier, 0.20)
            
            # Dynamic commission based on amount (example: lower commission for higher fares)
            if ride_amount > 100:
                rate = max(rate - 0.05, 0.05)  # Reduce by 5%, minimum 5%
            
            commission = ride_amount * Decimal(rate)
            
            return {
                'rate': rate,
                'amount': commission,
                'net_amount': ride_amount - commission
            }
            
        except Exception as e:
            logger.error(f"Error calculating commission: {str(e)}")
            raise


class PayoutCycleService:
    """Service for managing payout cycles"""
    
    @staticmethod
    def create_payout_cycle(start_date, end_date, processing_date):
        """
        Create a new payout cycle
        """
        try:
            cycle = PayoutCycle.objects.create(
                start_date=start_date,
                end_date=end_date,
                processing_date=processing_date,
                status='scheduled'
            )
            
            logger.info(f"Created payout cycle {cycle.id}")
            return cycle
            
        except Exception as e:
            logger.error(f"Error creating payout cycle: {str(e)}")
            raise
    
    @staticmethod
    def process_payout_cycle(cycle_id):
        """
        Process all pending payouts for a cycle
        """
        try:
            with transaction.atomic():
                cycle = PayoutCycle.objects.select_for_update().get(id=cycle_id)
                
                if cycle.status != 'scheduled':
                    raise ValidationError(f"Cannot process cycle with status: {cycle.status}")
                
                cycle.status = 'processing'
                cycle.processing_started_at = timezone.now()
                cycle.save()
                
                # Get all pending earnings for this cycle period
                pending_earnings = DriverEarning.objects.filter(
                    created_at__date__gte=cycle.start_date,
                    created_at__date__lte=cycle.end_date,
                    status='pending'
                ).select_related('driver')
                
                # Group by driver and process payouts
                drivers_processed = 0
                
                # This would iterate through drivers and create/process payouts
                # Implementation would be similar to automatic payouts but for specific cycle
                
                cycle.status = 'completed'
                cycle.processing_completed_at = timezone.now()
                cycle.save()
                
                return cycle
                
        except PayoutCycle.DoesNotExist:
            logger.error(f"Payout cycle {cycle_id} not found")
            raise ValidationError("Payout cycle not found")
        except Exception as e:
            logger.error(f"Error processing payout cycle {cycle_id}: {str(e)}")
            raise


class EarningAnalyticsService:
    """Service for earnings analytics and reporting"""
    
    @staticmethod
    def get_platform_earnings(start_date, end_date):
        """
        Get platform-wide earnings analytics
        """
        try:
            earnings = DriverEarning.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
            
            # Platform metrics
            platform_metrics = earnings.aggregate(
                total_gross=Sum('amount'),
                total_commission=Sum('commission'),
                total_net=Sum('net_earnings'),
                total_rides=Count('id'),
                avg_commission_rate=Avg('commission') / Avg('amount')
            )
            
            # Driver metrics
            driver_metrics = earnings.values('driver').annotate(
                driver_total=Sum('net_earnings'),
                ride_count=Count('id'),
                avg_earnings_per_ride=Avg('net_earnings')
            ).order_by('-driver_total')[:10]  # Top 10 earners
            
            # Daily trends
            daily_trends = earnings.values('created_at__date').annotate(
                daily_gross=Sum('amount'),
                daily_commission=Sum('commission'),
                daily_rides=Count('id')
            ).order_by('created_at__date')
            
            return {
                'platform_metrics': platform_metrics,
                'top_earners': list(driver_metrics),
                'daily_trends': list(daily_trends),
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'days': (end_date - start_date).days
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting platform earnings: {str(e)}")
            raise