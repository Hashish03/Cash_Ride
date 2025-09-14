from rest_framework import serializers
from .models import DriverEarning, Payout
from rides.serializers import RideSerializer

class DriverEarningSerializer(serializers.ModelSerializer):
    ride = RideSerializer(read_only=True)
    
    class Meta:
        model = DriverEarning
        fields = [
            'id', 'ride', 'amount', 'commission', 'net_earnings',
            'payment_status', 'payment_date', 'transaction_reference',
            'created_at'
        ]
        read_only_fields = fields

class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            'id', 'amount', 'status', 'method', 'reference',
            'initiated_at', 'processed_at'
        ]
        read_only_fields = fields

class PayoutRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    method = serializers.CharField(max_length=50)