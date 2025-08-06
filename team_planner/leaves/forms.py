from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta

from .models import LeaveRequest, LeaveType

User = get_user_model()


class LeaveRequestForm(forms.ModelForm):
    """Form for creating leave requests."""
    
    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "days_requested", "reason"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "days_requested": forms.NumberInput(attrs={"step": "0.5", "min": "0.5", "class": "form-control"}),
            "reason": forms.Textarea(attrs={"rows": 4, "placeholder": "Please provide reason for leave request...", "class": "form-control"}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Filter to only active leave types
        self.fields["leave_type"].queryset = LeaveType.objects.filter(is_active=True).order_by("name")
        
        # Add help text
        self.fields["start_date"].help_text = _("First day of leave")
        self.fields["end_date"].help_text = _("Last day of leave (inclusive)")
        self.fields["days_requested"].help_text = _("Total number of days requested (can be partial days)")
        
        # Set minimum date to today
        today = date.today()
        self.fields["start_date"].widget.attrs["min"] = today.isoformat()
        self.fields["end_date"].widget.attrs["min"] = today.isoformat()
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        days_requested = cleaned_data.get("days_requested")
        
        if start_date and end_date:
            # Validate date range
            if start_date > end_date:
                raise ValidationError(_("Start date must be before or equal to end date."))
            
            # Validate start date is not in the past
            if start_date < date.today():
                raise ValidationError(_("Start date cannot be in the past."))
            
            # Calculate working days and validate days_requested
            date_range = end_date - start_date
            max_days = date_range.days + 1  # Include both start and end dates
            
            if days_requested and days_requested > max_days:
                raise ValidationError(
                    _("Days requested ({}) cannot exceed the number of days in the date range ({}).").format(
                        days_requested, max_days
                    )
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.employee = self.user
        
        if commit:
            instance.save()
        return instance


class LeaveRequestResponseForm(forms.ModelForm):
    """Form for approving/rejecting leave requests."""
    
    action = forms.ChoiceField(
        choices=[
            ("approve", _("Approve")),
            ("reject", _("Reject")),
        ],
        widget=forms.RadioSelect,
        required=True,
        label=_("Action")
    )
    
    class Meta:
        model = LeaveRequest
        fields = ["rejection_reason"]
        widgets = {
            "rejection_reason": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Reason for rejection (if applicable)...", "class": "form-control"}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rejection_reason"].required = False
        self.fields["rejection_reason"].help_text = _("Required if rejecting the request")
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        rejection_reason = cleaned_data.get("rejection_reason")
        
        if action == "reject" and not rejection_reason:
            raise ValidationError({
                "rejection_reason": _("Rejection reason is required when rejecting a leave request.")
            })
        
        return cleaned_data


class LeaveRequestSearchForm(forms.Form):
    """Form for searching and filtering leave requests."""
    
    STATUS_CHOICES = [("", _("All Statuses"))] + list(LeaveRequest.Status.choices)
    
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=False,
        empty_label=_("All Employees"),
        widget=forms.Select(attrs={"class": "form-control"})
    )
    leave_type = forms.ModelChoiceField(
        queryset=LeaveType.objects.filter(is_active=True).order_by("name"),
        required=False,
        empty_label=_("All Leave Types"),
        widget=forms.Select(attrs={"class": "form-control"})
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    start_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label=_("Start Date From")
    )
    start_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label=_("Start Date To")
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # If user is not superuser, limit employee choices to themselves
        if user and not user.is_superuser:
            self.fields["employee"].queryset = User.objects.filter(pk=user.pk)
            self.fields["employee"].initial = user


class BulkLeaveApprovalForm(forms.Form):
    """Form for bulk approval/rejection of leave requests."""
    
    leave_requests = forms.ModelMultipleChoiceField(
        queryset=LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label=_("Select Leave Requests")
    )
    action = forms.ChoiceField(
        choices=[
            ("approve", _("Approve Selected")),
            ("reject", _("Reject Selected")),
        ],
        widget=forms.RadioSelect,
        required=True,
        label=_("Action")
    )
    bulk_rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Reason for rejection (if applicable)...", "class": "form-control"}),
        required=False,
        label=_("Bulk Rejection Reason")
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Only show pending requests that the user can approve
        pending_requests = LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING)
        
        if user and not user.is_superuser:
            # Regular users might only see their team's requests (implement as needed)
            # For now, keep all pending requests for admin users
            pass
            
        self.fields["leave_requests"].queryset = pending_requests.select_related(
            "employee", "leave_type"
        ).order_by("start_date")
        
        self.fields["bulk_rejection_reason"].help_text = _(
            "This reason will be applied to all rejected requests if no individual reason is provided"
        )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        bulk_rejection_reason = cleaned_data.get("bulk_rejection_reason")
        
        if action == "reject" and not bulk_rejection_reason:
            raise ValidationError({
                "bulk_rejection_reason": _("Bulk rejection reason is required when rejecting requests.")
            })
        
        return cleaned_data
