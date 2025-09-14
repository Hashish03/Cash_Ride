from rest_framework import serializers
from .models import PaymentMethod, Transaction, Wallet, Payout
from users.models import User

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'payment_type', 'is_default', 'card_last4', 'card_brand', 
                 'card_exp_month', 'card_exp_year', 'wallet_provider', 'bank_name', 
                 'account_last4', 'created_at']
        read_only_fields = ['id', 'created_at', 'user']
    
    def validate(self, data):
        payment_type = data.get('payment_type')
        
        if payment_type == 'card' and not all(k in data for k in ['card_last4', 'card_brand']):
            raise serializers.ValidationError("Card details are required for card payment method")
        
        if payment_type == 'wallet' and 'wallet_provider' not in data:
            raise serializers.ValidationError("Wallet provider is required for wallet payment method")
        
        if payment_type == 'bank' and not all(k in data for k in ['bank_name', 'account_last4']):
            raise serializers.ValidationError("Bank details are required for bank payment method")
        
        return data

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'currency', 'status', 'transaction_id', 
                 'description', 'created_at', 'payment_method']
        read_only_fields = ['id', 'status', 'transaction_id', 'created_at', 'user']

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance', 'currency', 'updated_at']
        read_only_fields = fields

class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = ['id', 'amount', 'currency', 'status', 'payout_method', 
                 'payout_reference', 'initiated_at', 'processed_at']
        read_only_fields = ['id', 'status', 'initiated_at', 'processed_at', 'user']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payout amount must be positive")
        return value

class PaymentEstimateSerializer(serializers.Serializer):
    distance = serializers.FloatField(min_value=0)
    duration = serializers.FloatField(min_value=0)
    ride_type = serializers.CharField(max_length=50)
    surge_multiplier = serializers.FloatField(min_value=1, default=1)
    
    def validate(self, data):
        # Add any custom validation logic here
        return data