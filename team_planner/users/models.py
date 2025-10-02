from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
import pyotp
import qrcode
from io import BytesIO
import base64


class UserRole(models.TextChoices):
    """User role choices with hierarchy."""
    EMPLOYEE = 'employee', _('Employee')
    TEAM_LEAD = 'team_lead', _('Team Lead')
    SCHEDULER = 'scheduler', _('Scheduler')
    MANAGER = 'manager', _('Manager')
    ADMIN = 'admin', _('Administrator')


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
    
    # MFA and Role fields
    mfa_required = models.BooleanField(
        _('MFA Required'),
        default=False,
        help_text=_('Require MFA for this user')
    )
    role = models.CharField(
        _('Role'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.EMPLOYEE
    )

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


class TwoFactorDevice(models.Model):
    """Store TOTP devices for two-factor authentication."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='mfa_device',
        verbose_name=_('User')
    )
    secret_key = models.CharField(
        _('Secret Key'),
        max_length=32,
        help_text=_('Base32-encoded TOTP secret')
    )
    is_verified = models.BooleanField(
        _('Is Verified'),
        default=False,
        help_text=_('Has the user verified this device?')
    )
    backup_codes = models.JSONField(
        _('Backup Codes'),
        default=list,
        help_text=_('List of one-time backup codes')
    )
    last_used = models.DateTimeField(
        _('Last Used'),
        null=True,
        blank=True
    )
    device_name = models.CharField(
        _('Device Name'),
        max_length=100,
        default='Authenticator App'
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Two-Factor Device')
        verbose_name_plural = _('Two-Factor Devices')
    
    def __str__(self):
        return f"{self.user.username} - {self.device_name}"
    
    def generate_secret(self):
        """Generate a new TOTP secret."""
        self.secret_key = pyotp.random_base32()
        return self.secret_key
    
    def get_totp(self):
        """Get TOTP instance for this device."""
        return pyotp.TOTP(self.secret_key)
    
    def verify_token(self, token):
        """Verify a TOTP token."""
        totp = self.get_totp()
        return totp.verify(token, valid_window=1)  # Allow 30s clock drift
    
    def verify_backup_code(self, code):
        """Verify and consume a backup code."""
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            self.save()
            return True
        return False
    
    def generate_backup_codes(self, count=10):
        """Generate new backup codes."""
        import secrets
        self.backup_codes = [
            secrets.token_hex(4).upper() for _ in range(count)
        ]
        return self.backup_codes
    
    def get_qr_code(self):
        """Generate QR code for TOTP setup."""
        totp = self.get_totp()
        provisioning_uri = totp.provisioning_uri(
            name=self.user.email,
            issuer_name='Team Planner'
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"


class MFALoginAttempt(models.Model):
    """Track MFA login attempts for security monitoring."""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mfa_attempts'
    )
    success = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255, blank=True)
    failure_reason = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('invalid_token', 'Invalid Token'),
            ('expired_token', 'Expired Token'),
            ('too_many_attempts', 'Too Many Attempts'),
            ('device_not_verified', 'Device Not Verified'),
        ]
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('MFA Login Attempt')
        verbose_name_plural = _('MFA Login Attempts')
        ordering = ['-created']


class RegistrationToken(models.Model):
    """Email verification tokens for new user registration."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='registration_token'
    )
    token = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Registration Token')
        verbose_name_plural = _('Registration Tokens')
    
    def save(self, *args, **kwargs):
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(32)
        if not self.expires:
            from django.utils import timezone
            from datetime import timedelta
            self.expires = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires


class RolePermission(models.Model):
    """Define permissions for each role."""
    
    role = models.CharField(
        _('Role'),
        max_length=20,
        choices=UserRole.choices,
        unique=True
    )
    
    # Shift permissions
    can_view_own_shifts = models.BooleanField(_('Can View Own Shifts'), default=True)
    can_view_team_shifts = models.BooleanField(_('Can View Team Shifts'), default=False)
    can_view_all_shifts = models.BooleanField(_('Can View All Shifts'), default=False)
    can_create_shifts = models.BooleanField(_('Can Create Shifts'), default=False)
    can_edit_own_shifts = models.BooleanField(_('Can Edit Own Shifts'), default=False)
    can_edit_team_shifts = models.BooleanField(_('Can Edit Team Shifts'), default=False)
    can_delete_shifts = models.BooleanField(_('Can Delete Shifts'), default=False)
    
    # Swap permissions
    can_request_swap = models.BooleanField(_('Can Request Swap'), default=True)
    can_approve_swap = models.BooleanField(_('Can Approve Swap'), default=False)
    can_view_all_swaps = models.BooleanField(_('Can View All Swaps'), default=False)
    
    # Leave permissions
    can_request_leave = models.BooleanField(_('Can Request Leave'), default=True)
    can_approve_leave = models.BooleanField(_('Can Approve Leave'), default=False)
    can_view_team_leave = models.BooleanField(_('Can View Team Leave'), default=False)
    
    # Orchestration permissions
    can_run_orchestrator = models.BooleanField(_('Can Run Orchestrator'), default=False)
    can_override_fairness = models.BooleanField(_('Can Override Fairness'), default=False)
    can_manual_assign = models.BooleanField(_('Can Manual Assign'), default=False)
    
    # Team permissions
    can_manage_team = models.BooleanField(_('Can Manage Team'), default=False)
    can_view_team_analytics = models.BooleanField(_('Can View Team Analytics'), default=False)
    
    # Reporting permissions
    can_view_reports = models.BooleanField(_('Can View Reports'), default=False)
    can_export_data = models.BooleanField(_('Can Export Data'), default=False)
    
    # User management
    can_manage_users = models.BooleanField(_('Can Manage Users'), default=False)
    can_assign_roles = models.BooleanField(_('Can Assign Roles'), default=False)
    
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Role Permission')
        verbose_name_plural = _('Role Permissions')
    
    def __str__(self):
        return f"{self.get_role_display()} Permissions"
    
    @classmethod
    def get_role_hierarchy(cls):
        """Return roles in hierarchical order (lowest to highest)."""
        return [
            UserRole.EMPLOYEE,
            UserRole.TEAM_LEAD,
            UserRole.SCHEDULER,
            UserRole.MANAGER,
            UserRole.ADMIN,
        ]
    
    @classmethod
    def has_higher_role(cls, user_role, target_role):
        """Check if user_role is higher than target_role in hierarchy."""
        hierarchy = cls.get_role_hierarchy()
        try:
            user_idx = hierarchy.index(user_role)
            target_idx = hierarchy.index(target_role)
            return user_idx > target_idx
        except ValueError:
            return False
