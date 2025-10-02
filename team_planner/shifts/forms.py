from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import Shift
from .models import SwapRequest

User = get_user_model()


class SwapRequestForm(forms.ModelForm):
    """Form for creating swap requests."""

    class Meta:
        model = SwapRequest
        fields = ["target_employee", "target_shift", "reason"]
        widgets = {
            "reason": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Explain why you need this swap..."},
            ),
        }

    def __init__(self, *args, **kwargs):
        self.requesting_employee = kwargs.pop("requesting_employee", None)
        self.requesting_shift = kwargs.pop("requesting_shift", None)
        super().__init__(*args, **kwargs)

        # Filter target employees to exclude the requesting employee
        if self.requesting_employee:
            self.fields["target_employee"].queryset = (
                User.objects.filter(is_active=True)
                .exclude(pk=self.requesting_employee.pk)
                .order_by("username")
            )

        # Filter target shifts based on selected target employee
        self.fields["target_shift"].queryset = Shift.objects.none()
        self.fields["target_shift"].required = False

        # Make target_shift optional with help text
        self.fields["target_shift"].help_text = _(
            "Optional: Select a specific shift from the target employee to swap with. "
            "If empty, the target employee will simply take over your shift.",
        )

    def clean(self):
        cleaned_data = super().clean()
        target_employee = cleaned_data.get("target_employee")
        target_shift = cleaned_data.get("target_shift")

        # If target_shift is selected, ensure it belongs to target_employee
        if target_shift and target_employee:
            if target_shift.assigned_employee != target_employee:
                msg = "Selected target shift must belong to the target employee."
                raise forms.ValidationError(
                    msg,
                )

        return cleaned_data


class SwapRequestResponseForm(forms.ModelForm):
    """Form for responding to swap requests."""

    class Meta:
        model = SwapRequest
        fields = ["response_notes"]
        widgets = {
            "response_notes": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Add a note about your decision..."},
            ),
        }


class ShiftSearchForm(forms.Form):
    """Form for searching available shifts for swapping."""

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        help_text=_("Filter shifts starting from this date"),
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        help_text=_("Filter shifts ending before this date"),
    )
    shift_type = forms.ChoiceField(
        choices=[("", "All Types")],  # Populated dynamically in __init__
        required=False,
        help_text=_("Filter by shift type"),
    )
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=False,
        empty_label="All Employees",
        help_text=_("Filter by assigned employee"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate shift types dynamically to avoid database queries at import time
        try:
            shift_types = Shift.objects.values_list("template__shift_type", "template__shift_type").distinct()
            self.fields["shift_type"].choices = [("", "All Types"), *list(shift_types)]
        except:
            # If database is not ready (migrations not run), keep default
            pass



class BulkSwapApprovalForm(forms.Form):
    """Form for bulk approval/rejection of swap requests."""

    swap_requests = forms.ModelMultipleChoiceField(
        queryset=SwapRequest.objects.filter(status="pending"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    action = forms.ChoiceField(
        choices=[
            ("approve", _("Approve Selected")),
            ("reject", _("Reject Selected")),
        ],
        widget=forms.RadioSelect,
        required=True,
    )
    bulk_response_notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text=_("Optional notes to add to all selected swap requests"),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter swap requests based on user permissions
        if user and not user.is_superuser:
            # Team leads can only approve swaps for their team members
            if (
                hasattr(user, "employee_profile")
                and user.employee_profile.teams.exists()
            ):
                team_members = User.objects.filter(
                    employee_profile__teams__in=user.employee_profile.teams.all(),
                )
                self.fields["swap_requests"].queryset = SwapRequest.objects.filter(
                    status="pending", requesting_employee__in=team_members,
                )
            else:
                # Regular users cannot use bulk approval
                self.fields["swap_requests"].queryset = SwapRequest.objects.none()
