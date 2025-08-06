from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import LeaveRequest, LeaveType

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (minimal)."""
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name']
    
    def get_name(self, obj):
        """Get user's display name."""
        return getattr(obj, 'name', str(obj))


class LeaveTypeSerializer(serializers.ModelSerializer):
    """Serializer for LeaveType model."""
    
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'description', 'default_days_per_year', 'requires_approval', 'is_paid', 'is_active', 'color']


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serializer for LeaveRequest model."""
    employee = UserSerializer(read_only=True)
    leave_type = LeaveTypeSerializer(read_only=True)
    leave_type_id = serializers.IntegerField(write_only=True)
    approved_by = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_be_approved = serializers.SerializerMethodField()
    has_shift_conflicts = serializers.ReadOnlyField()
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'leave_type', 'leave_type_id', 
            'start_date', 'end_date', 'days_requested', 'reason', 'status', 'status_display',
            'approved_by', 'approved_at', 'rejection_reason', 'created', 'modified',
            'can_be_approved', 'has_shift_conflicts'
        ]
        read_only_fields = ['id', 'employee', 'status', 'approved_by', 'approved_at', 'created', 'modified']
    
    def get_can_be_approved(self, obj):
        """Check if the request can be approved."""
        return obj.status == 'pending'
    
    def validate(self, attrs):
        """Validate leave request data."""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Start date cannot be after end date.")
        
        # Calculate days_requested if not provided
        if start_date and end_date and 'days_requested' not in attrs:
            days = (end_date - start_date).days + 1  # Include both start and end date
            attrs['days_requested'] = days
        
        return attrs
    
    def create(self, validated_data):
        """Create a new leave request."""
        leave_type_id = validated_data.pop('leave_type_id')
        try:
            leave_type = LeaveType.objects.get(id=leave_type_id)
        except LeaveType.DoesNotExist:
            raise serializers.ValidationError("Invalid leave type.")
        
        validated_data['leave_type'] = leave_type
        validated_data['status'] = 'pending'
        
        return super().create(validated_data)
