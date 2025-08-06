"""
Forms for the orchestrator system.
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date, timedelta

from .models import OrchestrationRun


class OrchestrationForm(forms.ModelForm):
    """Form for creating orchestration runs."""
    
    preview_only = forms.BooleanField(
        label=_("Preview Only"),
        required=False,
        initial=True,
        help_text=_("Generate preview without creating actual shifts")
    )
    
    class Meta:
        model = OrchestrationRun
        fields = ['name', 'description', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default date range (next Monday to end of year)
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday is 0
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        next_monday = today + timedelta(days=days_ahead)
        end_of_year = date(today.year, 12, 31)
        
        self.fields['start_date'].initial = next_monday
        self.fields['end_date'].initial = end_of_year
        
        # Add CSS classes for styling
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError(_("End date must be after start date."))
            
            if start_date < date.today():
                raise forms.ValidationError(_("Start date cannot be in the past."))
            
            # Check date range isn't too large (more than 2 years)
            if (end_date - start_date).days > 730:
                raise forms.ValidationError(_("Date range cannot exceed 2 years."))
        
        return cleaned_data


class DateRangeForm(forms.Form):
    """Simple form for date range selection."""
    
    start_date = forms.DateField(
        label=_("Start Date"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label=_("End Date"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Default to current year
        today = date.today()
        self.fields['start_date'].initial = date(today.year, 1, 1)
        self.fields['end_date'].initial = date(today.year, 12, 31)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError(_("End date must be after start date."))
        
        return cleaned_data
