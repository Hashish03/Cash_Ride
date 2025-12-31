import uuid
import json
import hashlib
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from django.utils import timezone
from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import Transaction, PaymentMethod, Refund, Wallet
from users.models import User
import logging
import requests
from enum import Enum

logger = logging.getLogger(__name__)


class PaymentStatus(Enum):
    """Payment status enumeration"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'
    PARTIALLY_REFUNDED = 'partially_refunded'


class PaymentGateway(Enum):
    """Supported payment gateways"""
    STRIPE = 'stripe'
    PAYPAL = 'paypal'
    RAZORPAY = 'razorpay'
    SQUARE = 'square'
    CASH = 'cash'
    WALLET = 'wallet'


class PaymentService:
    """Service for handling payment processing and management"""
    
    def __init__(self):
        """Initialize payment service with gateway configurations"""
        self.gateway_configs = {
            PaymentGateway.STRIPE.value: {
                'api_key': settings.STRIPE_SECRET_KEY,
                'public_key': settings.STRIPE_PUBLIC_KEY,
                'webhook_secret': settings.STRIPE_WEBHOOK_SECRET,
                'base_url': 'https://api.stripe.com/v1'
            },
            PaymentGateway.PAYPAL.value: {
                'client_id': settings.PAYPAL_CLIENT_ID,
                'client_secret': settings.PAYPAL_CLIENT_SECRET,
                'mode': settings.PAYPAL_MODE,
                'base_url': 'https://api.paypal.com' if settings.PAYPAL_MODE == 'live' 
                           else 'https://api.sandbox.paypal.com'
            },
            PaymentGateway.RAZORPAY.value: {
                'key_id': settings.RAZORPAY_KEY_ID,
                'key_secret': settings.RAZORPAY_KEY_SECRET,
                'base_url': 'https://api.razorpay.com/v1'
            }
        }
    
    def process_payment(self, user: User, amount: Decimal, payment_method_data: Dict, 
                       description: Optional[str] = None, metadata: Optional[Dict] = None) -> Transaction:
        """
        Process a payment transaction with proper gateway integration.
        
        Args:
            user: The user making the payment
            amount: Payment amount
            payment_method_data: Payment method details (card, wallet, etc.)
            description: Optional payment description
            metadata: Additional metadata for the transaction
            
        Returns:
            Transaction object
        """
        try:
            # Validate inputs
            self._validate_payment_inputs(user, amount, payment_method_data)
            
            # Generate unique transaction ID
            transaction_id = self._generate_transaction_id()
            
            # Determine payment gateway
            gateway = self._determine_payment_gateway(payment_method_data)
            
            # Create pending transaction
            transaction = Transaction.objects.create(
                user=user,
                transaction_id=transaction_id,
                amount=amount,
                currency='Rand ',
                gateway=gateway.value,
                payment_method_type=payment_method_data.get('type', 'card'),
                status=PaymentStatus.PENDING.value,
                description=description or "Payment for services",
                metadata={
                    'user_id': str(user.id),
                    'email': user.email,
                    'gateway': gateway.value,
                    'timestamp': timezone.now().isoformat(),
                    'ip_address': metadata.get('ip_address') if metadata else None,
                    'user_agent': metadata.get('user_agent') if metadata else None,
                    **(metadata or {})
                }
            )
            
            # Process based on gateway
            if gateway == PaymentGateway.WALLET:
                return self._process_wallet_payment(user, amount, transaction, payment_method_data)
            elif gateway == PaymentGateway.CASH:
                return self._process_cash_payment(transaction)
            else:
                return self._process_gateway_payment(gateway, amount, transaction, payment_method_data)
                
        except Exception as e:
            logger.error(f"Error processing payment for user {user.id}: {str(e)}", 
                        exc_info=True, extra={'user_id': user.id, 'amount': amount})
            raise ValidationError(f"Payment processing failed: {str(e)}")
    
    def _validate_payment_inputs(self, user: User, amount: Decimal, payment_method_data: Dict) -> None:
        """Validate payment inputs"""
        if amount <= Decimal('0.00'):
            raise ValidationError("Amount must be greater than zero")
        
        if amount > Decimal('100000.00'):  # Maximum single transaction limit
            raise ValidationError("Amount exceeds maximum transaction limit")
        
        if not user.is_active:
            raise ValidationError("User account is not active")
        
        required_fields = ['type']
        for field in required_fields:
            if field not in payment_method_data:
                raise ValidationError(f"Missing required field: {field}")
    
    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID"""
        timestamp = int(timezone.now().timestamp())
        random_str = uuid.uuid4().hex[:8]
        return f"txn_{timestamp}_{random_str}"
    
    def _determine_payment_gateway(self, payment_method_data: Dict) -> PaymentGateway:
        """Determine which payment gateway to use"""
        payment_type = payment_method_data.get('type', '').lower()
        
        if payment_type == 'wallet':
            return PaymentGateway.WALLET
        elif payment_type == 'cash':
            return PaymentGateway.CASH
        elif payment_type == 'card' and settings.DEFAULT_PAYMENT_GATEWAY == 'stripe':
            return PaymentGateway.STRIPE
        elif payment_type == 'paypal':
            return PaymentGateway.PAYPAL
        else:
            # Default to configured gateway
            return PaymentGateway(settings.DEFAULT_PAYMENT_GATEWAY)
    
    def _process_wallet_payment(self, user: User, amount: Decimal, 
                               transaction: Transaction, payment_method_data: Dict) -> Transaction:
        """Process payment using user's wallet"""
        try:
            with db_transaction.atomic():
                # Get or create user wallet
                wallet, created = Wallet.objects.get_or_create(
                    user=user,
                    defaults={'balance': Decimal('0.00')}
                )
                
                # Check wallet balance
                if wallet.balance < amount:
                    transaction.status = PaymentStatus.FAILED.value
                    transaction.metadata['failure_reason'] = 'Insufficient wallet balance'
                    transaction.save()
                    raise ValidationError("Insufficient wallet balance")
                
                # Deduct from wallet
                wallet.balance -= amount
                wallet.save()
                
                # Update transaction
                transaction.status = PaymentStatus.COMPLETED.value
                transaction.metadata.update({
                    'wallet_transaction': True,
                    'previous_balance': str(wallet.balance + amount),
                    'new_balance': str(wallet.balance)
                })
                transaction.save()
                
                # Record wallet transaction
                wallet.transactions.create(
                    transaction_type='debit',
                    amount=amount,
                    description=f"Payment: {transaction.description}",
                    reference_id=transaction.transaction_id,
                    balance_after=wallet.balance
                )
                
                logger.info(f"Wallet payment completed for user {user.id}, transaction {transaction.transaction_id}")
                return transaction
                
        except Exception as e:
            logger.error(f"Wallet payment failed for user {user.id}: {str(e)}")
            transaction.status = PaymentStatus.FAILED.value
            transaction.metadata['failure_reason'] = str(e)
            transaction.save()
            raise
    
    def _process_cash_payment(self, transaction: Transaction) -> Transaction:
        """Process cash payment (marks as pending until confirmed)"""
        transaction.status = PaymentStatus.PENDING.value
        transaction.metadata['cash_payment'] = True
        transaction.metadata['requires_confirmation'] = True
        transaction.save()
        
        # In real app, this would trigger cash collection workflow
        # For now, we'll simulate completion after delay
        logger.info(f"Cash payment initiated: {transaction.transaction_id}")
        return transaction
    
    def _process_gateway_payment(self, gateway: PaymentGateway, amount: Decimal,
                                transaction: Transaction, payment_method_data: Dict) -> Transaction:
        """Process payment through external gateway"""
        try:
            # Update transaction status to processing
            transaction.status = PaymentStatus.PROCESSING.value
            transaction.save()
            
            # Process based on gateway
            if gateway == PaymentGateway.STRIPE:
                return self._process_stripe_payment(amount, transaction, payment_method_data)
            elif gateway == PaymentGateway.PAYPAL:
                return self._process_paypal_payment(amount, transaction, payment_method_data)
            elif gateway == PaymentGateway.RAZORPAY:
                return self._process_razorpay_payment(amount, transaction, payment_method_data)
            else:
                raise ValidationError(f"Unsupported payment gateway: {gateway}")
                
        except Exception as e:
            logger.error(f"Gateway payment failed: {str(e)}")
            transaction.status = PaymentStatus.FAILED.value
            transaction.metadata['gateway_error'] = str(e)
            transaction.save()
            raise
    
    def _process_stripe_payment(self, amount: Decimal, transaction: Transaction, 
                               payment_method_data: Dict) -> Transaction:
        """Process payment through Stripe"""
        try:
            stripe_config = self.gateway_configs[PaymentGateway.STRIPE.value]
            
            # Convert amount to cents for Stripe
            amount_cents = int(amount * 100)
            
            # In a real implementation, you would:
            # 1. Create or use a Stripe Customer
            # 2. Create a PaymentIntent
            # 3. Confirm the payment
            
            # Mock implementation for now
            # This would be replaced with actual Stripe API calls
            headers = {
                'Authorization': f'Bearer {stripe_config["api_key"]}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'amount': amount_cents,
                'currency': transaction.currency.lower(),
                'payment_method': payment_method_data.get('payment_method_id'),
                'confirm': 'true',
                'metadata': {
                    'transaction_id': transaction.transaction_id,
                    'user_id': str(transaction.user.id)
                }
            }
            
            # Real API call would be:
            # response = requests.post(f"{stripe_config['base_url']}/payment_intents", 
            #                         headers=headers, data=data)
            
            # For mock purposes, simulate success
            mock_success = True  # In real app, check response.status_code == 200
            
            if mock_success:
                transaction.status = PaymentStatus.COMPLETED.value
                transaction.metadata.update({
                    'stripe_payment_intent_id': f'pi_mock_{uuid.uuid4().hex[:8]}',
                    'gateway_response': 'Mock successful response'
                })
                transaction.save()
                
                logger.info(f"Stripe payment completed: {transaction.transaction_id}")
                return transaction
            else:
                raise ValidationError("Stripe payment failed")
                
        except Exception as e:
            logger.error(f"Stripe payment error: {str(e)}")
            raise
    
    def _process_paypal_payment(self, amount: Decimal, transaction: Transaction,
                               payment_method_data: Dict) -> Transaction:
        """Process payment through PayPal"""
        # Similar implementation for PayPal
        # Would include OAuth2 token acquisition and order creation
        transaction.status = PaymentStatus.COMPLETED.value
        transaction.metadata['paypal_order_id'] = f'paypal_mock_{uuid.uuid4().hex[:8]}'
        transaction.save()
        
        logger.info(f"PayPal payment completed: {transaction.transaction_id}")
        return transaction
    
    def _process_razorpay_payment(self, amount: Decimal, transaction: Transaction,
                                 payment_method_data: Dict) -> Transaction:
        """Process payment through Razorpay"""
        # Similar implementation for Razorpay
        transaction.status = PaymentStatus.COMPLETED.value
        transaction.metadata['razorpay_order_id'] = f'rzp_mock_{uuid.uuid4().hex[:8]}'
        transaction.save()
        
        logger.info(f"Razorpay payment completed: {transaction.transaction_id}")
        return transaction
    
    def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get current status of a payment transaction"""
        try:
            transaction = Transaction.objects.get(transaction_id=transaction_id)
            
            return {
                'transaction_id': transaction.transaction_id,
                'status': transaction.status,
                'amount': str(transaction.amount),
                'currency': transaction.currency,
                'created_at': transaction.created_at.isoformat(),
                'updated_at': transaction.updated_at.isoformat(),
                'metadata': transaction.metadata
            }
            
        except Transaction.DoesNotExist:
            raise ValidationError(f"Transaction not found: {transaction_id}")
    
    def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None,
                      reason: Optional[str] = None) -> Refund:
        """
        Process a refund for a payment.
        
        Args:
            transaction_id: Original transaction ID
            amount: Amount to refund (None for full refund)
            reason: Reason for refund
            
        Returns:
            Refund object
        """
        try:
            with db_transaction.atomic():
                # Get original transaction
                original_transaction = Transaction.objects.select_for_update().get(
                    transaction_id=transaction_id
                )
                
                # Validate refund eligibility
                if original_transaction.status != PaymentStatus.COMPLETED.value:
                    raise ValidationError("Cannot refund non-completed transaction")
                
                # Calculate refund amount
                refund_amount = amount or original_transaction.amount
                
                if refund_amount <= Decimal('0.00'):
                    raise ValidationError("Refund amount must be greater than zero")
                
                if refund_amount > original_transaction.amount:
                    raise ValidationError("Refund amount cannot exceed original amount")
                
                # Check existing refunds
                existing_refunds = Refund.objects.filter(transaction=original_transaction)
                total_refunded = sum(refund.amount for refund in existing_refunds)
                
                if total_refunded + refund_amount > original_transaction.amount:
                    raise ValidationError(f"Cannot refund more than original amount. "
                                        f"Already refunded: {total_refunded}")
                
                # Create refund record
                refund = Refund.objects.create(
                    transaction=original_transaction,
                    refund_id=f"ref_{uuid.uuid4().hex[:8]}",
                    amount=refund_amount,
                    currency=original_transaction.currency,
                    reason=reason or "Customer request",
                    status='pending'
                )
                
                # Process refund based on original gateway
                if original_transaction.gateway == PaymentGateway.WALLET.value:
                    self._process_wallet_refund(original_transaction, refund)
                else:
                    self._process_gateway_refund(original_transaction, refund)
                
                # Update original transaction status
                if total_refunded + refund_amount == original_transaction.amount:
                    original_transaction.status = PaymentStatus.REFUNDED.value
                else:
                    original_transaction.status = PaymentStatus.PARTIALLY_REFUNDED.value
                original_transaction.save()
                
                logger.info(f"Refund processed: {refund.refund_id} for transaction {transaction_id}")
                return refund
                
        except Transaction.DoesNotExist:
            raise ValidationError(f"Transaction not found: {transaction_id}")
        except Exception as e:
            logger.error(f"Refund processing failed for {transaction_id}: {str(e)}")
            raise
    
    def _process_wallet_refund(self, transaction: Transaction, refund: Refund) -> None:
        """Process wallet refund"""
        try:
            wallet = Wallet.objects.get(user=transaction.user)
            wallet.balance += refund.amount
            wallet.save()
            
            refund.status = 'completed'
            refund.completed_at = timezone.now()
            refund.save()
            
            # Record wallet transaction
            wallet.transactions.create(
                transaction_type='credit',
                amount=refund.amount,
                description=f"Refund: {refund.reason}",
                reference_id=refund.refund_id,
                balance_after=wallet.balance
            )
            
        except Wallet.DoesNotExist:
            # Create wallet if it doesn't exist
            wallet = Wallet.objects.create(
                user=transaction.user,
                balance=refund.amount
            )
            refund.status = 'completed'
            refund.completed_at = timezone.now()
            refund.save()
    
    def _process_gateway_refund(self, transaction: Transaction, refund: Refund) -> None:
        """Process refund through original payment gateway"""
        # Mock gateway refund processing
        # In real app, this would call the gateway's refund API
        refund.status = 'completed'
        refund.completed_at = timezone.now()
        refund.gateway_refund_id = f"{transaction.gateway}_ref_{uuid.uuid4().hex[:8]}"
        refund.save()
    
    def verify_webhook(self, gateway: str, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature from payment gateway.
        
        Args:
            gateway: Payment gateway name
            payload: Raw webhook payload
            signature: Webhook signature
            
        Returns:
            Boolean indicating if signature is valid
        """
        try:
            if gateway == PaymentGateway.STRIPE.value:
                # Stripe signature verification
                import stripe
                stripe.api_key = self.gateway_configs[gateway]['api_key']
                
                # In real implementation:
                # event = stripe.Webhook.construct_event(
                #     payload, signature, self.gateway_configs[gateway]['webhook_secret']
                # )
                # return event is not None
                return True  # Mock verification
                
            elif gateway == PaymentGateway.RAZORPAY.value:
                # Razorpay signature verification
                expected_signature = hashlib.sha256(
                    payload + self.gateway_configs[gateway]['key_secret'].encode()
                ).hexdigest()
                return expected_signature == signature
                
            else:
                logger.warning(f"Webhook verification not implemented for gateway: {gateway}")
                return True  # Accept all for unimplemented gateways
                
        except Exception as e:
            logger.error(f"Webhook verification failed: {str(e)}")
            return False
    
    def handle_webhook(self, gateway: str, event_data: Dict) -> None:
        """
        Handle webhook events from payment gateway.
        
        Args:
            gateway: Payment gateway name
            event_data: Webhook event data
        """
        try:
            event_type = event_data.get('type')
            
            if gateway == PaymentGateway.STRIPE.value:
                if event_type == 'payment_intent.succeeded':
                    self._handle_stripe_payment_success(event_data)
                elif event_type == 'payment_intent.payment_failed':
                    self._handle_stripe_payment_failure(event_data)
                elif event_type == 'charge.refunded':
                    self._handle_stripe_refund(event_data)
                    
            elif gateway == PaymentGateway.PAYPAL.value:
                # Handle PayPal webhooks
                pass
                
            elif gateway == PaymentGateway.RAZORPAY.value:
                # Handle Razorpay webhooks
                pass
                
            logger.info(f"Webhook handled: {gateway} - {event_type}")
            
        except Exception as e:
            logger.error(f"Webhook handling failed: {str(e)}")
            raise
    
    def _handle_stripe_payment_success(self, event_data: Dict) -> None:
        """Handle Stripe payment success webhook"""
        payment_intent = event_data.get('data', {}).get('object', {})
        transaction_id = payment_intent.get('metadata', {}).get('transaction_id')
        
        if transaction_id:
            try:
                transaction = Transaction.objects.get(transaction_id=transaction_id)
                transaction.status = PaymentStatus.COMPLETED.value
                transaction.metadata['stripe_payment_intent_id'] = payment_intent.get('id')
                transaction.metadata['webhook_received'] = True
                transaction.save()
                
                # Trigger any post-payment actions
                self._trigger_post_payment_actions(transaction)
                
            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found for Stripe webhook: {transaction_id}")
    
    def _handle_stripe_payment_failure(self, event_data: Dict) -> None:
        """Handle Stripe payment failure webhook"""
        payment_intent = event_data.get('data', {}).get('object', {})
        transaction_id = payment_intent.get('metadata', {}).get('transaction_id')
        
        if transaction_id:
            try:
                transaction = Transaction.objects.get(transaction_id=transaction_id)
                transaction.status = PaymentStatus.FAILED.value
                transaction.metadata['failure_reason'] = payment_intent.get('last_payment_error', {}).get('message')
                transaction.metadata['webhook_received'] = True
                transaction.save()
                
            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found for Stripe webhook: {transaction_id}")
    
    def _handle_stripe_refund(self, event_data: Dict) -> None:
        """Handle Stripe refund webhook"""
        charge = event_data.get('data', {}).get('object', {})
        # Update refund status based on webhook
        pass
    
    def _trigger_post_payment_actions(self, transaction: Transaction) -> None:
        """Trigger actions that should happen after successful payment"""
        # This could include:
        # - Sending confirmation emails
        # - Updating order status
        # - Triggering fulfillment processes
        # - Sending notifications
        pass
    
    def get_transaction_history(self, user: User, limit: int = 50, 
                               offset: int = 0) -> Dict[str, Any]:
        """
        Get payment transaction history for a user.
        
        Args:
            user: User object
            limit: Number of transactions to return
            offset: Pagination offset
            
        Returns:
            Dictionary with transaction history and metadata
        """
        transactions = Transaction.objects.filter(user=user).order_by('-created_at')
        
        total_count = transactions.count()
        paginated_transactions = transactions[offset:offset + limit]
        
        return {
            'transactions': [
                {
                    'id': tx.id,
                    'transaction_id': tx.transaction_id,
                    'amount': str(tx.amount),
                    'currency': tx.currency,
                    'status': tx.status,
                    'gateway': tx.gateway,
                    'description': tx.description,
                    'created_at': tx.created_at.isoformat(),
                    'metadata': tx.metadata
                }
                for tx in paginated_transactions
            ],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        }
    
    def capture_cash_payment(self, transaction_id: str, collector_id: str, 
                            collected_amount: Decimal) -> Transaction:
        """
        Capture and confirm a cash payment.
        
        Args:
            transaction_id: Transaction ID
            collector_id: ID of person collecting cash
            collected_amount: Amount actually collected
            
        Returns:
            Updated transaction
        """
        try:
            with db_transaction.atomic():
                transaction = Transaction.objects.select_for_update().get(
                    transaction_id=transaction_id,
                    gateway=PaymentGateway.CASH.value
                )
                
                if transaction.status != PaymentStatus.PENDING.value:
                    raise ValidationError("Only pending cash payments can be captured")
                
                # Update transaction
                transaction.status = PaymentStatus.COMPLETED.value
                transaction.metadata.update({
                    'cash_collected_at': timezone.now().isoformat(),
                    'cash_collector_id': collector_id,
                    'collected_amount': str(collected_amount),
                    'original_amount': str(transaction.amount)
                })
                
                # Handle partial payment or overpayment
                if collected_amount < transaction.amount:
                    transaction.metadata['partial_payment'] = True
                    # In real app, you might create a new transaction for remaining amount
                elif collected_amount > transaction.amount:
                    transaction.metadata['overpayment'] = True
                    # In real app, you might handle overpayment (refund or credit)
                
                transaction.save()
                
                logger.info(f"Cash payment captured: {transaction_id} by collector {collector_id}")
                return transaction
                
        except Transaction.DoesNotExist:
            raise ValidationError(f"Cash transaction not found: {transaction_id}")
    
    def cancel_pending_payment(self, transaction_id: str) -> Transaction:
        """
        Cancel a pending payment.
        
        Args:
            transaction_id: Transaction ID to cancel
            
        Returns:
            Updated transaction
        """
        try:
            transaction = Transaction.objects.get(transaction_id=transaction_id)
            
            if transaction.status not in [PaymentStatus.PENDING.value, PaymentStatus.PROCESSING.value]:
                raise ValidationError(f"Cannot cancel payment with status: {transaction.status}")
            
            transaction.status = PaymentStatus.CANCELLED.value
            transaction.metadata['cancelled_at'] = timezone.now().isoformat()
            transaction.save()
            
            # If it was a wallet payment, return funds
            if transaction.gateway == PaymentGateway.WALLET.value:
                wallet = Wallet.objects.get(user=transaction.user)
                wallet.balance += transaction.amount
                wallet.save()
                
                # Record wallet transaction
                wallet.transactions.create(
                    transaction_type='credit',
                    amount=transaction.amount,
                    description=f"Cancelled payment: {transaction.description}",
                    reference_id=transaction.transaction_id,
                    balance_after=wallet.balance
                )
            
            logger.info(f"Payment cancelled: {transaction_id}")
            return transaction
            
        except Transaction.DoesNotExist:
            raise ValidationError(f"Transaction not found: {transaction_id}")


# Singleton instance for easy access
payment_service = PaymentService()