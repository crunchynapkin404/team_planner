from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Default custom user model for Team Planner.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    def get_full_name(self) -> str:
        """Override to use the name field instead of first_name + last_name."""
        return self.name.strip() if self.name else self.username

    def get_short_name(self) -> str:
        """Override to use the name field."""
        return self.first_name_display or self.username

    @property
    def display_name(self) -> str:
        """Get the display name for the user."""
        return self.name.strip() if self.name else self.username
    
    @property
    def first_name_display(self) -> str:
        """Get first name for compatibility with frontend."""
        parts = self.name.split() if self.name else []
        return parts[0] if parts else ""
    
    @property  
    def last_name_display(self) -> str:
        """Get last name for compatibility with frontend."""
        parts = self.name.split() if self.name else []
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})
