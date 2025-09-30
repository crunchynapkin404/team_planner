from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import LeaveRequest
from .models import LeaveType

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (minimal)."""

    display_name = serializers.SerializerMethodField()

    class Meta:  # type: ignore[override]
        model = User  # type: ignore[assignment]
        fields = ["id", "email", "username", "first_name", "last_name", "display_name"]

    def get_display_name(self, obj):
        """Get user's display name."""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        if obj.first_name:
            return obj.first_name
        if obj.last_name:
            return obj.last_name
        return obj.username or obj.email


class LeaveTypeSerializer(serializers.ModelSerializer):
    """Serializer for LeaveType model."""

    conflict_handling_display = serializers.CharField(
        source="get_conflict_handling_display", read_only=True,
    )

    class Meta:  # type: ignore[override]
        model = LeaveType  # type: ignore[assignment]
        fields = [
            "id",
            "name",
            "description",
            "default_days_per_year",
            "requires_approval",
            "is_paid",
            "is_active",
            "color",
            "conflict_handling",
            "conflict_handling_display",
            "start_time",
            "end_time",
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serializer for LeaveRequest model."""

    employee = UserSerializer(read_only=True)
    leave_type = LeaveTypeSerializer(read_only=True)
    leave_type_id = serializers.IntegerField(write_only=True)
    approved_by = UserSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    recurrence_type_display = serializers.CharField(
        source="get_recurrence_type_display", read_only=True,
    )
    can_be_approved = serializers.SerializerMethodField()
    has_shift_conflicts = serializers.ReadOnlyField()
    effective_start_time = serializers.SerializerMethodField()
    effective_end_time = serializers.SerializerMethodField()
    blocking_message = serializers.SerializerMethodField()
    within_active_window = serializers.SerializerMethodField()

    class Meta:  # type: ignore[override]
        model = LeaveRequest  # type: ignore[assignment]
        fields = [
            "id",
            "employee",
            "leave_type",
            "leave_type_id",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "days_requested",
            "reason",
            "status",
            "status_display",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "created",
            "modified",
            "can_be_approved",
            "has_shift_conflicts",
            "blocking_message",
            "within_active_window",
            "is_recurring",
            "recurrence_type",
            "recurrence_type_display",
            "recurrence_end_date",
            "parent_request",
            "effective_start_time",
            "effective_end_time",
        ]
        read_only_fields = [
            "id",
            "employee",
            "status",
            "approved_by",
            "approved_at",
            "created",
            "modified",
        ]

    def get_can_be_approved(self, obj):
        """Check if the request can be approved."""
        return obj.can_be_approved()

    def get_effective_start_time(self, obj):
        """Get the effective start time for this leave request."""
        time_obj = obj.get_effective_start_time()
        return time_obj.strftime("%H:%M") if time_obj else None

    def get_effective_end_time(self, obj):
        """Get the effective end time for this leave request."""
        time_obj = obj.get_effective_end_time()
        return time_obj.strftime("%H:%M") if time_obj else None

    def get_blocking_message(self, obj):
        """Provide reason why approval is blocked, if any."""
        return obj.get_blocking_message()

    def get_within_active_window(self, obj):
        """Whether the leave is within the active planning window."""
        try:
            return obj.is_within_active_planning_window()
        except Exception:
            return False

    def validate(self, attrs):
        """Validate leave request data."""
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        is_recurring = attrs.get("is_recurring", False)
        recurrence_end_date = attrs.get("recurrence_end_date")

        if start_date and end_date and start_date > end_date:
            msg = "Start date cannot be after end date."
            raise serializers.ValidationError(msg)

        # Validate recurring leave
        if is_recurring:
            if not recurrence_end_date:
                msg = "Recurrence end date is required for recurring leave."
                raise serializers.ValidationError(
                    msg,
                )
            if recurrence_end_date <= start_date:
                msg = "Recurrence end date must be after start date."
                raise serializers.ValidationError(
                    msg,
                )

        # Calculate days_requested if not provided
        if start_date and end_date and "days_requested" not in attrs:
            days = (end_date - start_date).days + 1  # Include both start and end date
            attrs["days_requested"] = days

        return attrs

    def create(self, validated_data):
        """Create a new leave request and handle recurring instances."""
        leave_type_id = validated_data.pop("leave_type_id")
        try:
            leave_type = LeaveType.objects.get(id=leave_type_id)
        except LeaveType.DoesNotExist:
            msg = "Invalid leave type."
            raise serializers.ValidationError(msg)

        validated_data["leave_type"] = leave_type
        validated_data["status"] = "pending"

        # Create the main request
        leave_request = super().create(validated_data)

        # Create recurring instances if requested
        if leave_request.is_recurring:
            leave_request.create_recurring_instances()

        return leave_request
