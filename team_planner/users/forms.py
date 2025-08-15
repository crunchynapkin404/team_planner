from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


class RecurringLeavePatternForm(forms.ModelForm):
    """Form for creating/editing recurring leave patterns."""
    
    class Meta:
        from team_planner.employees.models import RecurringLeavePattern
        model = RecurringLeavePattern
        fields = [
            'name',
            'day_of_week', 
            'frequency',
            'coverage_type',
            'pattern_start_date',
            'effective_from',
            'effective_until',
            'is_active',
            'notes'
        ]
        widgets = {
            'pattern_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'effective_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'effective_until': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
            'coverage_type': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add help text for better UX
        self.fields['name'].help_text = _("Give this pattern a descriptive name (e.g., 'Monday Mornings Off', 'Bi-weekly Tuesday Afternoons')")
        self.fields['pattern_start_date'].help_text = _("For biweekly patterns, this determines which weeks the pattern applies")
        self.fields['effective_from'].help_text = _("When should this pattern start being applied?")
        self.fields['effective_until'].help_text = _("Leave blank for permanent pattern")
        
        # Set some sensible defaults
        if not self.instance.pk:
            from datetime import date
            self.fields['effective_from'].initial = date.today()
            self.fields['pattern_start_date'].initial = date.today()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.employee = self.user
        if commit:
            instance.save()
        return instance


class RecurringLeavePatternFormSet(forms.BaseInlineFormSet):
    """Formset for managing multiple recurring leave patterns."""
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['user'] = self.user
        return kwargs


# Create the actual formset class
from django.forms import inlineformset_factory
from team_planner.employees.models import RecurringLeavePattern

RecurringLeavePatternInlineFormSet = inlineformset_factory(
    parent_model=User,
    model=RecurringLeavePattern,
    form=RecurringLeavePatternForm,
    formset=RecurringLeavePatternFormSet,
    fields=[
        'name',
        'day_of_week',
        'frequency', 
        'coverage_type',
        'pattern_start_date',
        'effective_from',
        'effective_until',
        'is_active',
        'notes'
    ],
    extra=1,
    can_delete=True,
    widgets={
        'pattern_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        'effective_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        'effective_until': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        'name': forms.TextInput(attrs={'class': 'form-control'}),
        'day_of_week': forms.Select(attrs={'class': 'form-control'}),
        'frequency': forms.Select(attrs={'class': 'form-control'}),
        'coverage_type': forms.Select(attrs={'class': 'form-control'}),
        'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    }
)


class UserProfileForm(forms.ModelForm):
    """Enhanced user form that includes basic profile information."""
    
    class Meta:
        model = User
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = _("Your full name as it should appear in schedules")
