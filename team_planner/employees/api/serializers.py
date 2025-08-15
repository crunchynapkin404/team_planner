from rest_framework import serializers
from team_planner.employees.models import RecurringLeavePattern


class RecurringLeavePatternSerializer(serializers.ModelSerializer):
    """Serializer for RecurringLeavePattern model."""
    
    class Meta:
        model = RecurringLeavePattern
        fields = [
            'id',
            'employee',
            'name',
            'day_of_week',
            'frequency',
            'coverage_type',
            'pattern_start_date',
            'effective_from',
            'effective_until',
            'is_active',
            'notes',
            'created',
            'modified'
        ]
        read_only_fields = ['id', 'employee', 'created', 'modified']
    
    def validate(self, attrs):
        """Custom validation for RecurringLeavePattern."""
        if attrs.get('effective_until') and attrs.get('effective_from'):
            if attrs['effective_until'] <= attrs['effective_from']:
                raise serializers.ValidationError(
                    "Effective until date must be after effective from date."
                )
        return attrs
