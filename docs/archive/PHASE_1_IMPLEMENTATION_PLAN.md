# Phase 1 Implementation Plan - Security & Notifications
## Team Planner - 8-10 Week MVP Roadmap

**Created:** October 1, 2025  
**Timeline:** 8-10 weeks  
**Budget:** $40,000 - $50,000  
**Team:** 2 developers + 1 QA engineer

---

## Table of Contents

1. [Week 1-2: Multi-Factor Authentication (MFA)](#week-1-2-mfa)
2. [Week 3-4: Role-Based Access Control (RBAC)](#week-3-4-rbac)
3. [Week 5-6: Notification System](#week-5-6-notifications)
4. [Week 7-8: Essential Reports & Exports](#week-7-8-reports)
5. [Week 9-10: Testing & Deployment](#week-9-10-testing)

---

## Week 1-2: Multi-Factor Authentication (MFA)

### Overview
Implement TOTP-based two-factor authentication for all users with backup codes.

### Technical Specifications

#### 1. Database Models

**File:** `team_planner/users/models.py`

```python
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from team_planner.contrib.sites.models import TimeStampedModel
import pyotp
import qrcode
from io import BytesIO
import base64

User = get_user_model()


class TwoFactorDevice(TimeStampedModel):
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


class MFALoginAttempt(TimeStampedModel):
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
    
    class Meta:
        verbose_name = _('MFA Login Attempt')
        verbose_name_plural = _('MFA Login Attempts')
        ordering = ['-created']
```

#### 2. Migration

**File:** `team_planner/users/migrations/000X_add_mfa.py`

```python
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('users', '000X_previous_migration'),
    ]

    operations = [
        migrations.CreateModel(
            name='TwoFactorDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('secret_key', models.CharField(max_length=32)),
                ('is_verified', models.BooleanField(default=False)),
                ('backup_codes', models.JSONField(default=list)),
                ('last_used', models.DateTimeField(blank=True, null=True)),
                ('device_name', models.CharField(default='Authenticator App', max_length=100)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, 
                                             related_name='mfa_device', to='users.user')),
            ],
            options={
                'verbose_name': 'Two-Factor Device',
                'verbose_name_plural': 'Two-Factor Devices',
            },
        ),
        migrations.CreateModel(
            name='MFALoginAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('success', models.BooleanField(default=False)),
                ('ip_address', models.GenericIPAddressField()),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('failure_reason', models.CharField(blank=True, max_length=100)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                          related_name='mfa_attempts', to='users.user')),
            ],
            options={
                'verbose_name': 'MFA Login Attempt',
                'verbose_name_plural': 'MFA Login Attempts',
                'ordering': ['-created'],
            },
        ),
        # Add MFA required field to User model
        migrations.AddField(
            model_name='user',
            name='mfa_required',
            field=models.BooleanField(default=False, 
                                     help_text='Require MFA for this user'),
        ),
    ]
```

#### 3. Views & API Endpoints

**File:** `team_planner/users/api/mfa_views.py`

```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from ..models import TwoFactorDevice, MFALoginAttempt

User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_mfa(request):
    """
    Initialize MFA setup for the current user.
    Returns QR code and secret key.
    """
    user = request.user
    
    # Create or get device
    device, created = TwoFactorDevice.objects.get_or_create(user=user)
    
    if created or not device.is_verified:
        # Generate new secret
        device.generate_secret()
        device.generate_backup_codes()
        device.is_verified = False
        device.save()
    
    return Response({
        'secret': device.secret_key,
        'qr_code': device.get_qr_code(),
        'backup_codes': device.backup_codes,
        'is_verified': device.is_verified,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_mfa(request):
    """
    Verify MFA setup with a token.
    Required fields: token
    """
    user = request.user
    token = request.data.get('token')
    
    if not token:
        return Response(
            {'error': 'Token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        device = user.mfa_device
    except TwoFactorDevice.DoesNotExist:
        return Response(
            {'error': 'MFA not set up for this user'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if device.verify_token(token):
        device.is_verified = True
        device.last_used = timezone.now()
        device.save()
        
        # Log successful verification
        MFALoginAttempt.objects.create(
            user=user,
            success=True,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'success': True,
            'message': 'MFA verified successfully',
            'backup_codes': device.backup_codes
        })
    else:
        # Log failed attempt
        MFALoginAttempt.objects.create(
            user=user,
            success=False,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            failure_reason='invalid_token'
        )
        
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disable_mfa(request):
    """
    Disable MFA for the current user.
    Requires current password and MFA token.
    """
    user = request.user
    password = request.data.get('password')
    token = request.data.get('token')
    
    # Verify password
    if not user.check_password(password):
        return Response(
            {'error': 'Invalid password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        device = user.mfa_device
        
        # Verify token before disabling
        if not device.verify_token(token):
            return Response(
                {'error': 'Invalid MFA token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        device.delete()
        
        return Response({
            'success': True,
            'message': 'MFA disabled successfully'
        })
    except TwoFactorDevice.DoesNotExist:
        return Response(
            {'error': 'MFA not enabled for this user'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
def mfa_login_verify(request):
    """
    Verify MFA token during login.
    Used after initial username/password authentication.
    """
    from rest_framework.authtoken.models import Token
    
    user_id = request.session.get('mfa_user_id')
    token = request.data.get('token')
    use_backup = request.data.get('use_backup', False)
    
    if not user_id:
        return Response(
            {'error': 'No pending MFA authentication'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(id=user_id)
        device = user.mfa_device
        
        # Verify token or backup code
        if use_backup:
            verified = device.verify_backup_code(token)
            if verified and len(device.backup_codes) < 3:
                # Warn user they're running low on backup codes
                pass
        else:
            verified = device.verify_token(token)
        
        if verified:
            device.last_used = timezone.now()
            device.save()
            
            # Log successful login
            MFALoginAttempt.objects.create(
                user=user,
                success=True,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Clear session
            del request.session['mfa_user_id']
            
            # Generate auth token
            token, _ = Token.objects.get_or_create(user=user)
            
            return Response({
                'success': True,
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'backup_codes_remaining': len(device.backup_codes)
            })
        else:
            # Log failed attempt
            MFALoginAttempt.objects.create(
                user=user,
                success=False,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                failure_reason='invalid_token'
            )
            
            return Response(
                {'error': 'Invalid token or backup code'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except (User.DoesNotExist, TwoFactorDevice.DoesNotExist):
        return Response(
            {'error': 'Invalid authentication state'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mfa_status(request):
    """Get MFA status for current user."""
    user = request.user
    
    try:
        device = user.mfa_device
        return Response({
            'enabled': True,
            'verified': device.is_verified,
            'device_name': device.device_name,
            'last_used': device.last_used,
            'backup_codes_remaining': len(device.backup_codes)
        })
    except TwoFactorDevice.DoesNotExist:
        return Response({
            'enabled': False,
            'verified': False
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_backup_codes(request):
    """
    Regenerate backup codes.
    Requires current password and MFA token.
    """
    user = request.user
    password = request.data.get('password')
    token = request.data.get('token')
    
    if not user.check_password(password):
        return Response(
            {'error': 'Invalid password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        device = user.mfa_device
        
        if not device.verify_token(token):
            return Response(
                {'error': 'Invalid MFA token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        backup_codes = device.generate_backup_codes()
        device.save()
        
        return Response({
            'success': True,
            'backup_codes': backup_codes,
            'message': 'New backup codes generated. Save these securely!'
        })
    except TwoFactorDevice.DoesNotExist:
        return Response(
            {'error': 'MFA not enabled'},
            status=status.HTTP_400_BAD_REQUEST
        )


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

#### 4. URL Configuration

**File:** `team_planner/users/api/urls.py` (add to existing)

```python
from django.urls import path
from . import mfa_views

urlpatterns = [
    # ... existing URLs ...
    
    # MFA endpoints
    path('mfa/setup/', mfa_views.setup_mfa, name='mfa-setup'),
    path('mfa/verify/', mfa_views.verify_mfa, name='mfa-verify'),
    path('mfa/disable/', mfa_views.disable_mfa, name='mfa-disable'),
    path('mfa/status/', mfa_views.mfa_status, name='mfa-status'),
    path('mfa/login/verify/', mfa_views.mfa_login_verify, name='mfa-login-verify'),
    path('mfa/backup-codes/regenerate/', mfa_views.regenerate_backup_codes, 
         name='mfa-regenerate-backup-codes'),
]
```

#### 5. Frontend Components

**File:** `frontend/src/components/auth/MFASetup.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Stepper,
  Step,
  StepLabel,
  Alert,
  Chip,
  Grid,
} from '@mui/material';
import { QrCode2, Security, VpnKey } from '@mui/icons-material';
import apiClient from '../../services/apiClient';

interface MFASetupProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const MFASetup: React.FC<MFASetupProps> = ({ open, onClose, onSuccess }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [qrCode, setQrCode] = useState('');
  const [secret, setSecret] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [verificationToken, setVerificationToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const steps = ['Scan QR Code', 'Verify Token', 'Save Backup Codes'];

  useEffect(() => {
    if (open) {
      initializeMFA();
    }
  }, [open]);

  const initializeMFA = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post('/api/users/mfa/setup/');
      setQrCode(response.data.qr_code);
      setSecret(response.data.secret);
      setBackupCodes(response.data.backup_codes);
      setActiveStep(0);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to initialize MFA');
    } finally {
      setLoading(false);
    }
  };

  const verifyToken = async () => {
    setLoading(true);
    setError('');
    try {
      await apiClient.post('/api/users/mfa/verify/', {
        token: verificationToken,
      });
      setActiveStep(2);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Invalid token');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = () => {
    onSuccess();
    onClose();
  };

  const handleNext = () => {
    if (activeStep === 0) {
      setActiveStep(1);
    } else if (activeStep === 1) {
      verifyToken();
    } else {
      handleComplete();
    }
  };

  const handleBack = () => {
    setActiveStep(activeStep - 1);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const downloadBackupCodes = () => {
    const element = document.createElement('a');
    const file = new Blob([backupCodes.join('\n')], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = 'team-planner-backup-codes.txt';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Security color="primary" />
          Enable Two-Factor Authentication
        </Box>
      </DialogTitle>
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Step 1: QR Code */}
        {activeStep === 0 && (
          <Box textAlign="center">
            <Typography variant="body1" gutterBottom>
              Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
            </Typography>
            {qrCode && (
              <Box my={2}>
                <img src={qrCode} alt="MFA QR Code" style={{ maxWidth: '300px' }} />
              </Box>
            )}
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Or enter this key manually:
            </Typography>
            <Box display="flex" alignItems="center" justifyContent="center" gap={1}>
              <Chip 
                label={secret} 
                onClick={() => copyToClipboard(secret)}
                icon={<VpnKey />}
              />
              <Button size="small" onClick={() => copyToClipboard(secret)}>
                Copy
              </Button>
            </Box>
          </Box>
        )}

        {/* Step 2: Verify */}
        {activeStep === 1 && (
          <Box>
            <Typography variant="body1" gutterBottom>
              Enter the 6-digit code from your authenticator app to verify setup
            </Typography>
            <TextField
              fullWidth
              label="Verification Code"
              value={verificationToken}
              onChange={(e) => setVerificationToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              inputProps={{ maxLength: 6, style: { fontSize: '24px', textAlign: 'center' } }}
              sx={{ my: 2 }}
            />
          </Box>
        )}

        {/* Step 3: Backup Codes */}
        {activeStep === 2 && (
          <Box>
            <Alert severity="warning" sx={{ mb: 2 }}>
              Save these backup codes in a secure place. You can use them to access your account
              if you lose your authenticator device.
            </Alert>
            <Grid container spacing={1}>
              {backupCodes.map((code, index) => (
                <Grid item xs={6} key={index}>
                  <Chip 
                    label={code} 
                    sx={{ fontFamily: 'monospace', width: '100%' }}
                  />
                </Grid>
              ))}
            </Grid>
            <Box mt={2} display="flex" gap={1}>
              <Button
                variant="outlined"
                onClick={() => copyToClipboard(backupCodes.join('\n'))}
                fullWidth
              >
                Copy All
              </Button>
              <Button
                variant="outlined"
                onClick={downloadBackupCodes}
                fullWidth
              >
                Download
              </Button>
            </Box>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        {activeStep > 0 && activeStep < 2 && (
          <Button onClick={handleBack}>Back</Button>
        )}
        <Button
          variant="contained"
          onClick={handleNext}
          disabled={loading || (activeStep === 1 && verificationToken.length !== 6)}
        >
          {activeStep === 2 ? 'Finish' : 'Next'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MFASetup;
```

#### 6. Dependencies

**File:** `requirements/base.txt` (add these)

```txt
# MFA dependencies
pyotp==2.9.0
qrcode[pil]==7.4.2
```

#### 7. Settings Configuration

**File:** `config/settings/base.py` (add this)

```python
# MFA Settings
MFA_REQUIRED_FOR_STAFF = True  # Require MFA for staff users
MFA_TOKEN_VALIDITY_WINDOW = 1  # Allow 30s clock drift
MFA_BACKUP_CODES_COUNT = 10
MFA_MAX_ATTEMPTS = 5  # Max failed attempts before lockout
MFA_LOCKOUT_DURATION = 900  # 15 minutes lockout
```

### Testing Checklist

- [ ] User can enable MFA
- [ ] QR code displays correctly
- [ ] Manual secret key works
- [ ] Token verification works
- [ ] Backup codes work
- [ ] User can disable MFA
- [ ] Login flow requires MFA token
- [ ] Backup codes can be regenerated
- [ ] Failed attempts are logged
- [ ] Rate limiting works

### Deployment Steps

1. Install dependencies: `pip install pyotp qrcode[pil]`
2. Run migrations: `python manage.py migrate`
3. Update frontend with new components
4. Configure settings in production
5. Test with real authenticator apps
6. Update user documentation

### Estimated Effort

- Backend development: 3 days
- Frontend development: 2 days
- Testing: 2 days
- Documentation: 1 day
- **Total: 8 days (1.5 weeks)**

---

## Week 2.5: User Registration & Onboarding

### Overview
Add user self-registration with email verification and role assignment workflow.

### Technical Specifications

#### 1. Backend - Registration API

**File:** `team_planner/users/api/registration_views.py`

```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets

User = get_user_model()


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
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires:
            self.expires = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user account.
    Sends email verification.
    """
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    name = request.data.get('name')
    
    # Validation
    if not all([username, email, password, name]):
        return Response(
            {'error': 'All fields are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already registered'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create user (inactive until email verified)
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        name=name,
        is_active=False,
        role='employee'  # Default role
    )
    
    # Create verification token
    token = RegistrationToken.objects.create(user=user)
    
    # Send verification email
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token.token}"
    send_mail(
        subject='Verify your Team Planner account',
        message=f'Click this link to verify your email: {verification_url}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    
    return Response({
        'success': True,
        'message': 'Registration successful. Please check your email to verify your account.',
        'user_id': user.id
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    """Verify email with token."""
    token_str = request.data.get('token')
    
    if not token_str:
        return Response(
            {'error': 'Token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        token = RegistrationToken.objects.get(token=token_str)
    except RegistrationToken.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not token.is_valid:
        return Response(
            {'error': 'Token has expired or already been used'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Activate user
    user = token.user
    user.is_active = True
    user.save()
    
    token.is_used = True
    token.save()
    
    return Response({
        'success': True,
        'message': 'Email verified successfully. You can now log in.',
        'username': user.username
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification(request):
    """Resend verification email."""
    email = request.data.get('email')
    
    try:
        user = User.objects.get(email=email, is_active=False)
    except User.DoesNotExist:
        return Response(
            {'error': 'No pending registration found for this email'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Delete old token and create new one
    RegistrationToken.objects.filter(user=user).delete()
    token = RegistrationToken.objects.create(user=user)
    
    # Send email
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token.token}"
    send_mail(
        subject='Verify your Team Planner account',
        message=f'Click this link to verify your email: {verification_url}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    
    return Response({
        'success': True,
        'message': 'Verification email sent'
    })
```

#### 2. Frontend - Registration Form

**File:** `frontend/src/components/auth/RegisterForm.tsx`

```tsx
import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  Link,
  CircularProgress,
} from '@mui/material';
import { PersonAdd } from '@mui/icons-material';
import { apiClient } from '../../services/apiClient';

const RegisterForm: React.FC = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    name: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    if (error) setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      setLoading(false);
      return;
    }

    try {
      const response = await apiClient.post('/api/auth/register/', {
        username: formData.username,
        email: formData.email,
        name: formData.name,
        password: formData.password,
      });

      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <Box sx={{ maxWidth: 400, mx: 'auto', mt: 8 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Alert severity="success" sx={{ mb: 2 }}>
            Registration successful! Please check your email to verify your account.
          </Alert>
          <Typography variant="body2" align="center">
            Didn't receive the email?{' '}
            <Link href="/resend-verification" underline="hover">
              Resend verification
            </Link>
          </Typography>
          <Button
            fullWidth
            variant="outlined"
            href="/login"
            sx={{ mt: 2 }}
          >
            Back to Login
          </Button>
        </Paper>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 400, mx: 'auto', mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box display="flex" alignItems="center" justifyContent="center" mb={3}>
          <PersonAdd sx={{ fontSize: 40, mr: 1, color: 'primary.main' }} />
          <Typography variant="h4">Create Account</Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label="Full Name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            margin="normal"
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            label="Username"
            name="username"
            value={formData.username}
            onChange={handleChange}
            margin="normal"
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            label="Email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            margin="normal"
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            label="Password"
            name="password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            margin="normal"
            required
            disabled={loading}
            helperText="Minimum 8 characters"
          />
          <TextField
            fullWidth
            label="Confirm Password"
            name="confirmPassword"
            type="password"
            value={formData.confirmPassword}
            onChange={handleChange}
            margin="normal"
            required
            disabled={loading}
          />
          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2 }}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : null}
          >
            {loading ? 'Creating Account...' : 'Sign Up'}
          </Button>
          <Typography variant="body2" align="center">
            Already have an account?{' '}
            <Link href="/login" underline="hover">
              Sign in
            </Link>
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};

export default RegisterForm;
```

#### 3. Add Registration Link to Login Page

**File:** `frontend/src/components/auth/LoginForm.tsx` (update)

```tsx
// Add after the Sign In button:
<Typography variant="body2" align="center" sx={{ mt: 2 }}>
  Don't have an account?{' '}
  <Link href="/register" underline="hover">
    Create one
  </Link>
</Typography>
```

#### 4. Email Verification Page

**File:** `frontend/src/pages/VerifyEmail.tsx`

```tsx
import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Box, Paper, Typography, CircularProgress, Alert, Button } from '@mui/material';
import { CheckCircle, Error } from '@mui/icons-material';
import { apiClient } from '../services/apiClient';

const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (!token) {
      setStatus('error');
      setMessage('Invalid verification link');
      return;
    }

    verifyEmail(token);
  }, [searchParams]);

  const verifyEmail = async (token: string) => {
    try {
      const response = await apiClient.post('/api/auth/verify-email/', { token });
      setStatus('success');
      setMessage(response.data.message);
      
      // Redirect to login after 3 seconds
      setTimeout(() => navigate('/login'), 3000);
    } catch (err: any) {
      setStatus('error');
      setMessage(err.response?.data?.error || 'Verification failed');
    }
  };

  return (
    <Box sx={{ maxWidth: 500, mx: 'auto', mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4, textAlign: 'center' }}>
        {status === 'loading' && (
          <>
            <CircularProgress size={60} sx={{ mb: 2 }} />
            <Typography variant="h6">Verifying your email...</Typography>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle color="success" sx={{ fontSize: 60, mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Email Verified!
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              {message}
            </Typography>
            <Typography variant="body2">
              Redirecting to login...
            </Typography>
          </>
        )}

        {status === 'error' && (
          <>
            <Error color="error" sx={{ fontSize: 60, mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Verification Failed
            </Typography>
            <Alert severity="error" sx={{ mb: 2 }}>
              {message}
            </Alert>
            <Button variant="contained" href="/login" fullWidth>
              Back to Login
            </Button>
          </>
        )}
      </Paper>
    </Box>
  );
};

export default VerifyEmail;
```

#### 5. URL Configuration

**File:** `config/api_router.py` (add)

```python
# Registration endpoints
path("auth/register/", registration_views.register_user, name="register"),
path("auth/verify-email/", registration_views.verify_email, name="verify-email"),
path("auth/resend-verification/", registration_views.resend_verification, name="resend-verification"),
```

**File:** `frontend/src/App.tsx` (add routes)

```tsx
<Route path="/register" element={<RegisterForm />} />
<Route path="/verify-email" element={<VerifyEmail />} />
```

#### 6. Settings Configuration

**File:** `config/settings/base.py` (add)

```python
# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@teamplanner.com')

# Frontend URL for email links
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3001')
```

### Testing Checklist

- [ ] User can register with valid credentials
- [ ] Duplicate username/email is rejected
- [ ] Password validation works
- [ ] Verification email is sent
- [ ] Email verification works
- [ ] Token expiration works (24 hours)
- [ ] User can resend verification email
- [ ] Inactive users cannot log in
- [ ] Link to registration from login page works

### Deployment Steps

1. Configure email settings (SMTP)
2. Run migrations for RegistrationToken model
3. Add frontend routes
4. Test email delivery
5. Update user documentation

### Estimated Effort

- Backend development: 1 day
- Frontend development: 1 day
- Email setup & testing: 0.5 days
- **Total: 2.5 days (0.5 weeks)**

---

## Week 3-4: Role-Based Access Control (RBAC)

### Overview
Implement granular permission system with role hierarchy.

### Technical Specifications

#### 1. Database Models

**File:** `team_planner/users/models.py` (add to existing)

```python
class UserRole(models.TextChoices):
    """User role choices with hierarchy."""
    EMPLOYEE = 'employee', _('Employee')
    TEAM_LEAD = 'team_lead', _('Team Lead')
    MANAGER = 'manager', _('Manager')
    SCHEDULER = 'scheduler', _('Scheduler')
    ADMIN = 'admin', _('Administrator')


class RolePermission(TimeStampedModel):
    """Define permissions for each role."""
    
    role = models.CharField(
        _('Role'),
        max_length=20,
        choices=UserRole.choices,
        unique=True
    )
    
    # Shift permissions
    can_view_own_shifts = models.BooleanField(default=True)
    can_view_team_shifts = models.BooleanField(default=False)
    can_view_all_shifts = models.BooleanField(default=False)
    can_create_shifts = models.BooleanField(default=False)
    can_edit_own_shifts = models.BooleanField(default=False)
    can_edit_team_shifts = models.BooleanField(default=False)
    can_delete_shifts = models.BooleanField(default=False)
    
    # Swap permissions
    can_request_swap = models.BooleanField(default=True)
    can_approve_swap = models.BooleanField(default=False)
    can_view_all_swaps = models.BooleanField(default=False)
    
    # Leave permissions
    can_request_leave = models.BooleanField(default=True)
    can_approve_leave = models.BooleanField(default=False)
    can_view_team_leave = models.BooleanField(default=False)
    
    # Orchestration permissions
    can_run_orchestrator = models.BooleanField(default=False)
    can_override_fairness = models.BooleanField(default=False)
    can_manual_assign = models.BooleanField(default=False)
    
    # Team permissions
    can_manage_team = models.BooleanField(default=False)
    can_view_team_analytics = models.BooleanField(default=False)
    
    # Reporting permissions
    can_view_reports = models.BooleanField(default=False)
    can_export_data = models.BooleanField(default=False)
    
    # User management
    can_manage_users = models.BooleanField(default=False)
    can_assign_roles = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Role Permission')
        verbose_name_plural = _('Role Permissions')
    
    def __str__(self):
        return f"{self.get_role_display()} Permissions"
    
    @classmethod
    def get_role_hierarchy(cls):
        """Return roles in hierarchical order."""
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


# Add to User model (extend existing)
User.add_to_class(
    'role',
    models.CharField(
        _('Role'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.EMPLOYEE
    )
)
```

#### 2. Permission Utilities

**File:** `team_planner/users/permissions.py`

```python
from rest_framework.permissions import BasePermission
from .models import RolePermission, UserRole


class HasRolePermission(BasePermission):
    """
    Custom permission to check role-based permissions.
    Usage: permission_classes = [HasRolePermission]
    Set permission_required on the view.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superusers bypass all checks
        if request.user.is_superuser:
            return True
        
        # Get required permission from view
        permission = getattr(view, 'permission_required', None)
        if not permission:
            return True  # No specific permission required
        
        return check_user_permission(request.user, permission)


class IsTeamLeadOrAbove(BasePermission):
    """User must be Team Lead or higher."""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        role_hierarchy = RolePermission.get_role_hierarchy()
        user_role = request.user.role
        team_lead_idx = role_hierarchy.index(UserRole.TEAM_LEAD)
        
        try:
            user_idx = role_hierarchy.index(user_role)
            return user_idx >= team_lead_idx
        except ValueError:
            return False


class IsManagerOrAbove(BasePermission):
    """User must be Manager or higher."""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return request.user.role in [UserRole.MANAGER, UserRole.ADMIN]


class CanManageTeam(BasePermission):
    """User can manage the specific team."""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check if user is team manager
        if hasattr(obj, 'manager') and obj.manager == request.user:
            return True
        
        # Check role permission
        return check_user_permission(request.user, 'can_manage_team')


def check_user_permission(user, permission_name):
    """
    Check if user has a specific permission based on role.
    
    Args:
        user: User instance
        permission_name: String name of permission (e.g., 'can_approve_swap')
    
    Returns:
        Boolean indicating if user has permission
    """
    if user.is_superuser:
        return True
    
    try:
        role_perms = RolePermission.objects.get(role=user.role)
        return getattr(role_perms, permission_name, False)
    except RolePermission.DoesNotExist:
        return False


def get_user_permissions(user):
    """Get all permissions for a user."""
    if user.is_superuser:
        # Superuser has all permissions
        return {
            field.name: True
            for field in RolePermission._meta.fields
            if field.name.startswith('can_')
        }
    
    try:
        role_perms = RolePermission.objects.get(role=user.role)
        return {
            field.name: getattr(role_perms, field.name)
            for field in RolePermission._meta.fields
            if field.name.startswith('can_')
        }
    except RolePermission.DoesNotExist:
        return {}


class RoleBasedViewMixin:
    """Mixin for views that require role-based permissions."""
    
    permission_required = None  # Set in subclass
    
    def check_permissions(self, request):
        super().check_permissions(request)
        
        if self.permission_required and not request.user.is_superuser:
            if not check_user_permission(request.user, self.permission_required):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    f"Your role does not have '{self.permission_required}' permission"
                )
```

#### 3. API Endpoints

**File:** `team_planner/users/api/rbac_views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from ..models import RolePermission, UserRole
from ..permissions import HasRolePermission, check_user_permission, get_user_permissions
from ..serializers import UserRoleSerializer, RolePermissionSerializer

User = get_user_model()


class RoleManagementViewSet(viewsets.ViewSet):
    """Manage user roles and permissions."""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_permissions(self, request):
        """Get current user's permissions."""
        permissions = get_user_permissions(request.user)
        return Response({
            'role': request.user.role,
            'role_display': request.user.get_role_display(),
            'permissions': permissions,
            'is_superuser': request.user.is_superuser
        })
    
    @action(detail=False, methods=['get'])
    def available_roles(self, request):
        """Get all available roles and their permissions."""
        if not request.user.is_superuser:
            # Non-superusers can only see roles at or below their level
            hierarchy = RolePermission.get_role_hierarchy()
            try:
                user_idx = hierarchy.index(request.user.role)
                available = hierarchy[:user_idx + 1]
            except ValueError:
                available = [UserRole.EMPLOYEE]
        else:
            available = RolePermission.get_role_hierarchy()
        
        roles_data = []
        for role in available:
            try:
                perms = RolePermission.objects.get(role=role)
                serializer = RolePermissionSerializer(perms)
                roles_data.append(serializer.data)
            except RolePermission.DoesNotExist:
                roles_data.append({
                    'role': role,
                    'role_display': UserRole(role).label
                })
        
        return Response(roles_data)
    
    @action(detail=True, methods=['post'], url_path='assign-role')
    def assign_role(self, request, pk=None):
        """Assign a role to a user."""
        if not check_user_permission(request.user, 'can_assign_roles'):
            return Response(
                {'error': 'You do not have permission to assign roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            target_user = User.objects.get(pk=pk)
            new_role = request.data.get('role')
            
            if new_role not in dict(UserRole.choices):
                return Response(
                    {'error': 'Invalid role'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Prevent assigning higher role than your own
            if not request.user.is_superuser:
                if RolePermission.has_higher_role(new_role, request.user.role):
                    return Response(
                        {'error': 'Cannot assign a role higher than your own'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Cannot change superuser role
            if target_user.is_superuser and not request.user.is_superuser:
                return Response(
                    {'error': 'Cannot modify superuser roles'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            target_user.role = new_role
            target_user.save()
            
            return Response({
                'success': True,
                'message': f'Role updated to {UserRole(new_role).label}',
                'user_id': target_user.id,
                'new_role': new_role
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
```

#### 4. Management Commands

**File:** `team_planner/users/management/commands/setup_roles.py`

```python
from django.core.management.base import BaseCommand
from team_planner.users.models import RolePermission, UserRole


class Command(BaseCommand):
    help = 'Set up default role permissions'

    def handle(self, *args, **options):
        """Create default permissions for all roles."""
        
        roles_config = {
            UserRole.EMPLOYEE: {
                'can_view_own_shifts': True,
                'can_request_swap': True,
                'can_request_leave': True,
            },
            UserRole.TEAM_LEAD: {
                'can_view_own_shifts': True,
                'can_view_team_shifts': True,
                'can_request_swap': True,
                'can_approve_swap': True,
                'can_request_leave': True,
                'can_approve_leave': True,
                'can_view_team_leave': True,
                'can_view_team_analytics': True,
            },
            UserRole.SCHEDULER: {
                'can_view_own_shifts': True,
                'can_view_team_shifts': True,
                'can_view_all_shifts': True,
                'can_create_shifts': True,
                'can_edit_team_shifts': True,
                'can_request_swap': True,
                'can_approve_swap': True,
                'can_request_leave': True,
                'can_view_team_leave': True,
                'can_run_orchestrator': True,
                'can_manual_assign': True,
                'can_view_reports': True,
                'can_export_data': True,
            },
            UserRole.MANAGER: {
                'can_view_own_shifts': True,
                'can_view_team_shifts': True,
                'can_view_all_shifts': True,
                'can_create_shifts': True,
                'can_edit_team_shifts': True,
                'can_delete_shifts': True,
                'can_request_swap': True,
                'can_approve_swap': True,
                'can_view_all_swaps': True,
                'can_request_leave': True,
                'can_approve_leave': True,
                'can_view_team_leave': True,
                'can_run_orchestrator': True,
                'can_override_fairness': True,
                'can_manual_assign': True,
                'can_manage_team': True,
                'can_view_team_analytics': True,
                'can_view_reports': True,
                'can_export_data': True,
                'can_manage_users': True,
            },
            UserRole.ADMIN: {
                # Admin has all permissions
                field.name: True
                for field in RolePermission._meta.fields
                if field.name.startswith('can_')
            }
        }
        
        for role, permissions in roles_config.items():
            role_perm, created = RolePermission.objects.get_or_create(
                role=role,
                defaults=permissions
            )
            
            if not created:
                # Update existing
                for perm, value in permissions.items():
                    setattr(role_perm, perm, value)
                role_perm.save()
            
            action = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{action} permissions for {UserRole(role).label}'
                )
            )
```

### Testing Checklist

- [ ] Role permissions created in database
- [ ] Users can be assigned roles
- [ ] Permission checks work correctly
- [ ] Role hierarchy enforced
- [ ] API endpoints respect permissions
- [ ] Frontend shows/hides features based on role
- [ ] Audit log tracks role changes

### Deployment Steps

1. Run migrations
2. Execute `python manage.py setup_roles`
3. Assign roles to existing users
4. Update API views with permission checks
5. Update frontend components
6. Test all permission combinations

### Estimated Effort

- Backend development: 4 days
- Frontend integration: 3 days
- Testing: 2 days
- Documentation: 1 day
- **Total: 10 days (2 weeks)**

---

## Week 5-6: Notification System

### Overview

Implement real-time notification system with WebSocket support, email templates, SMS integration, and user preferences.

### Technical Specifications

#### 1. Database Models

**File:** `team_planner/notifications/models.py`

```python
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from team_planner.contrib.sites.models import TimeStampedModel

User = get_user_model()


class NotificationType(models.TextChoices):
    """Types of notifications."""
    SHIFT_ASSIGNED = 'shift_assigned', _('Shift Assigned')
    SHIFT_CHANGED = 'shift_changed', _('Shift Changed')
    SHIFT_CANCELLED = 'shift_cancelled', _('Shift Cancelled')
    SWAP_REQUESTED = 'swap_requested', _('Swap Requested')
    SWAP_APPROVED = 'swap_approved', _('Swap Approved')
    SWAP_REJECTED = 'swap_rejected', _('Swap Rejected')
    LEAVE_APPROVED = 'leave_approved', _('Leave Approved')
    LEAVE_REJECTED = 'leave_rejected', _('Leave Rejected')
    SCHEDULE_PUBLISHED = 'schedule_published', _('Schedule Published')
    REMINDER_UPCOMING_SHIFT = 'reminder_upcoming', _('Upcoming Shift Reminder')
    OVERTIME_ALERT = 'overtime_alert', _('Overtime Alert')
    COVERAGE_GAP = 'coverage_gap', _('Coverage Gap')
    SYSTEM_ANNOUNCEMENT = 'system_announcement', _('System Announcement')


class NotificationChannel(models.TextChoices):
    """Delivery channels for notifications."""
    IN_APP = 'in_app', _('In-App')
    EMAIL = 'email', _('Email')
    SMS = 'sms', _('SMS')
    PUSH = 'push', _('Push Notification')


class Notification(TimeStampedModel):
    """Store all notifications."""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('User')
    )
    notification_type = models.CharField(
        _('Type'),
        max_length=30,
        choices=NotificationType.choices
    )
    title = models.CharField(_('Title'), max_length=255)
    message = models.TextField(_('Message'))
    
    # Related objects
    related_shift = models.ForeignKey(
        'shifts.Shift',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_swap = models.ForeignKey(
        'shifts.SwapRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_leave = models.ForeignKey(
        'leaves.LeaveRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    # Metadata
    data = models.JSONField(
        _('Additional Data'),
        default=dict,
        blank=True,
        help_text=_('Extra data for notification rendering')
    )
    
    # Status
    is_read = models.BooleanField(_('Is Read'), default=False)
    read_at = models.DateTimeField(_('Read At'), null=True, blank=True)
    
    # Delivery tracking
    sent_via = models.JSONField(
        _('Sent Via'),
        default=list,
        help_text=_('List of channels notification was sent through')
    )
    
    # Action
    action_url = models.CharField(
        _('Action URL'),
        max_length=500,
        blank=True,
        help_text=_('Frontend URL to navigate to when clicked')
    )
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user', '-created']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class NotificationPreference(TimeStampedModel):
    """User preferences for notification delivery."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('User')
    )
    
    # Channel preferences (per notification type)
    preferences = models.JSONField(
        _('Preferences'),
        default=dict,
        help_text=_('Notification type -> channels mapping')
    )
    
    # Global settings
    do_not_disturb_start = models.TimeField(
        _('Do Not Disturb Start'),
        null=True,
        blank=True,
        help_text=_('Start time for quiet hours')
    )
    do_not_disturb_end = models.TimeField(
        _('Do Not Disturb End'),
        null=True,
        blank=True,
        help_text=_('End time for quiet hours')
    )
    
    timezone = models.CharField(
        _('Timezone'),
        max_length=50,
        default='UTC'
    )
    
    # Contact info
    phone_number = models.CharField(
        _('Phone Number'),
        max_length=20,
        blank=True,
        help_text=_('For SMS notifications')
    )
    phone_verified = models.BooleanField(
        _('Phone Verified'),
        default=False
    )
    
    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
    
    def __str__(self):
        return f"{self.user.username} Notification Preferences"
    
    def get_channels_for_type(self, notification_type):
        """Get enabled channels for a notification type."""
        default_channels = [NotificationChannel.IN_APP, NotificationChannel.EMAIL]
        return self.preferences.get(notification_type, default_channels)
    
    def is_quiet_hours(self):
        """Check if currently in do-not-disturb hours."""
        if not self.do_not_disturb_start or not self.do_not_disturb_end:
            return False
        
        from django.utils import timezone
        import pytz
        
        tz = pytz.timezone(self.timezone)
        now = timezone.now().astimezone(tz).time()
        
        start = self.do_not_disturb_start
        end = self.do_not_disturb_end
        
        if start < end:
            return start <= now <= end
        else:
            # Crosses midnight
            return now >= start or now <= end


class NotificationTemplate(TimeStampedModel):
    """Email/SMS templates for notifications."""
    
    notification_type = models.CharField(
        _('Notification Type'),
        max_length=30,
        choices=NotificationType.choices,
        unique=True
    )
    
    # Email template
    email_subject = models.CharField(
        _('Email Subject'),
        max_length=255,
        help_text=_('Supports template variables: {{user}}, {{shift}}, etc.')
    )
    email_body_html = models.TextField(
        _('Email Body (HTML)'),
        help_text=_('HTML email template')
    )
    email_body_text = models.TextField(
        _('Email Body (Plain Text)'),
        help_text=_('Plain text fallback')
    )
    
    # SMS template
    sms_body = models.CharField(
        _('SMS Body'),
        max_length=160,
        blank=True,
        help_text=_('Max 160 characters')
    )
    
    # Push notification
    push_title = models.CharField(_('Push Title'), max_length=100, blank=True)
    push_body = models.CharField(_('Push Body'), max_length=200, blank=True)
    
    # In-app notification
    in_app_title = models.CharField(_('In-App Title'), max_length=255)
    in_app_message = models.TextField(_('In-App Message'))
    
    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
    
    def __str__(self):
        return f"Template: {self.get_notification_type_display()}"
    
    def render_email(self, context):
        """Render email template with context."""
        from django.template import Template, Context
        
        subject_template = Template(self.email_subject)
        html_template = Template(self.email_body_html)
        text_template = Template(self.email_body_text)
        
        ctx = Context(context)
        
        return {
            'subject': subject_template.render(ctx),
            'html_body': html_template.render(ctx),
            'text_body': text_template.render(ctx)
        }
```

#### 2. Notification Service

**File:** `team_planner/notifications/services.py`

```python
from typing import List, Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import (
    Notification,
    NotificationPreference,
    NotificationType,
    NotificationChannel,
    NotificationTemplate
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()


class NotificationService:
    """Centralized notification service."""
    
    @staticmethod
    def send_notification(
        user: User,
        notification_type: str,
        title: str,
        message: str,
        related_shift=None,
        related_swap=None,
        related_leave=None,
        action_url: str = '',
        data: Dict[str, Any] = None,
        force_channels: List[str] = None
    ) -> Notification:
        """
        Send a notification through appropriate channels.
        
        Args:
            user: Recipient user
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            related_shift: Related Shift object
            related_swap: Related SwapRequest object
            related_leave: Related LeaveRequest object
            action_url: Frontend URL for action
            data: Additional context data
            force_channels: Override user preferences with specific channels
        
        Returns:
            Created Notification instance
        """
        # Create notification record
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_shift=related_shift,
            related_swap=related_swap,
            related_leave=related_leave,
            action_url=action_url,
            data=data or {}
        )
        
        # Get user preferences
        try:
            prefs = user.notification_preferences
        except NotificationPreference.DoesNotExist:
            prefs = NotificationPreference.objects.create(user=user)
        
        # Determine channels
        if force_channels:
            channels = force_channels
        else:
            channels = prefs.get_channels_for_type(notification_type)
        
        # Check quiet hours (except for urgent notifications)
        urgent_types = [
            NotificationType.COVERAGE_GAP,
            NotificationType.SYSTEM_ANNOUNCEMENT
        ]
        if notification_type not in urgent_types and prefs.is_quiet_hours():
            # Only send in-app during quiet hours
            channels = [NotificationChannel.IN_APP]
        
        sent_via = []
        
        # Send via each channel
        for channel in channels:
            try:
                if channel == NotificationChannel.IN_APP:
                    NotificationService._send_in_app(notification)
                    sent_via.append(channel)
                
                elif channel == NotificationChannel.EMAIL:
                    NotificationService._send_email(notification, user)
                    sent_via.append(channel)
                
                elif channel == NotificationChannel.SMS:
                    if prefs.phone_verified:
                        NotificationService._send_sms(notification, user, prefs)
                        sent_via.append(channel)
                
                elif channel == NotificationChannel.PUSH:
                    NotificationService._send_push(notification, user)
                    sent_via.append(channel)
            
            except Exception as e:
                # Log error but don't fail entire notification
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send {channel} notification: {e}")
        
        # Update sent_via
        notification.sent_via = sent_via
        notification.save()
        
        return notification
    
    @staticmethod
    def _send_in_app(notification: Notification):
        """Send real-time in-app notification via WebSocket."""
        channel_layer = get_channel_layer()
        
        # Send to user's WebSocket channel
        async_to_sync(channel_layer.group_send)(
            f"user_{notification.user.id}",
            {
                "type": "notification_message",
                "notification": {
                    "id": notification.id,
                    "type": notification.notification_type,
                    "title": notification.title,
                    "message": notification.message,
                    "action_url": notification.action_url,
                    "created": notification.created.isoformat(),
                    "is_read": notification.is_read
                }
            }
        )
    
    @staticmethod
    def _send_email(notification: Notification, user: User):
        """Send email notification."""
        try:
            template = NotificationTemplate.objects.get(
                notification_type=notification.notification_type
            )
        except NotificationTemplate.DoesNotExist:
            # Use default template
            template = None
        
        if template:
            # Build context
            context = {
                'user': user,
                'notification': notification,
                'site_url': settings.FRONTEND_URL,
                **notification.data
            }
            
            rendered = template.render_email(context)
            
            msg = EmailMultiAlternatives(
                subject=rendered['subject'],
                body=rendered['text_body'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(rendered['html_body'], "text/html")
        else:
            # Simple email
            msg = EmailMultiAlternatives(
                subject=notification.title,
                body=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
        
        msg.send()
    
    @staticmethod
    def _send_sms(notification: Notification, user: User, prefs: NotificationPreference):
        """Send SMS notification via Twilio."""
        if not prefs.phone_number:
            return
        
        try:
            template = NotificationTemplate.objects.get(
                notification_type=notification.notification_type
            )
            sms_body = template.sms_body
        except NotificationTemplate.DoesNotExist:
            # Truncate message to 160 chars
            sms_body = notification.message[:160]
        
        # TODO: Integrate with Twilio
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(
        #     body=sms_body,
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=prefs.phone_number
        # )
        
        # For now, just log
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"SMS to {prefs.phone_number}: {sms_body}")
    
    @staticmethod
    def _send_push(notification: Notification, user: User):
        """Send push notification (for future PWA implementation)."""
        # TODO: Implement push notifications
        pass
    
    @staticmethod
    def notify_shift_assigned(shift, user):
        """Notify user of shift assignment."""
        return NotificationService.send_notification(
            user=user,
            notification_type=NotificationType.SHIFT_ASSIGNED,
            title="New Shift Assigned",
            message=f"You have been assigned to {shift.shift_template.name} on {shift.date}",
            related_shift=shift,
            action_url=f"/shifts/{shift.id}",
            data={
                'shift_id': shift.id,
                'shift_date': str(shift.date),
                'shift_name': shift.shift_template.name
            }
        )
    
    @staticmethod
    def notify_swap_request(swap_request):
        """Notify target employee of swap request."""
        return NotificationService.send_notification(
            user=swap_request.target_employee.user,
            notification_type=NotificationType.SWAP_REQUESTED,
            title="Shift Swap Request",
            message=f"{swap_request.requesting_employee.user.get_full_name()} wants to swap shifts with you",
            related_swap=swap_request,
            action_url=f"/swaps/{swap_request.id}",
            data={
                'swap_id': swap_request.id,
                'requester': swap_request.requesting_employee.user.get_full_name()
            }
        )
    
    @staticmethod
    def notify_leave_decision(leave_request, approved: bool):
        """Notify user of leave request decision."""
        status_text = "approved" if approved else "rejected"
        notification_type = (
            NotificationType.LEAVE_APPROVED if approved 
            else NotificationType.LEAVE_REJECTED
        )
        
        return NotificationService.send_notification(
            user=leave_request.employee.user,
            notification_type=notification_type,
            title=f"Leave Request {status_text.title()}",
            message=f"Your leave request from {leave_request.start_date} to {leave_request.end_date} has been {status_text}",
            related_leave=leave_request,
            action_url=f"/leave/{leave_request.id}",
            data={
                'leave_id': leave_request.id,
                'approved': approved
            }
        )
```

#### 3. WebSocket Consumer

**File:** `team_planner/notifications/consumers.py`

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Join user-specific group
        self.room_group_name = f"user_{self.user.id}"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send unread count on connect
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket."""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)
                
            elif action == 'mark_all_read':
                await self.mark_all_read()
                
            elif action == 'get_recent':
                notifications = await self.get_recent_notifications()
                await self.send(text_data=json.dumps({
                    'type': 'recent_notifications',
                    'notifications': notifications
                }))
        
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """Receive notification from room group."""
        notification = event['notification']
        
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': notification
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for user."""
        from .models import Notification
        return Notification.objects.filter(
            user=self.user,
            is_read=False
        ).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read."""
        from .models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_read(self):
        """Mark all notifications as read."""
        from .models import Notification
        from django.utils import timezone
        
        Notification.objects.filter(
            user=self.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
    
    @database_sync_to_async
    def get_recent_notifications(self, limit=20):
        """Get recent notifications."""
        from .models import Notification
        
        notifications = Notification.objects.filter(
            user=self.user
        ).select_related(
            'related_shift',
            'related_swap',
            'related_leave'
        )[:limit]
        
        return [
            {
                'id': n.id,
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'action_url': n.action_url,
                'created': n.created.isoformat(),
                'is_read': n.is_read
            }
            for n in notifications
        ]
```

### Testing Checklist

- [ ] Notifications created correctly
- [ ] WebSocket connections work
- [ ] Real-time delivery functional
- [ ] Email sending works
- [ ] User preferences respected
- [ ] Quiet hours enforced
- [ ] Templates render correctly
- [ ] Mark as read works

### Deployment Steps

1. Install dependencies: `pip install channels channels-redis twilio`
2. Configure Redis for channels
3. Run migrations
4. Set up email templates
5. Configure Twilio (optional)
6. Update WebSocket routing
7. Deploy with ASGI server (Daphne/Uvicorn)

### Estimated Effort

- Backend development: 5 days
- WebSocket setup: 2 days
- Frontend integration: 3 days
- Testing: 2 days
- **Total: 12 days (2.5 weeks)**

---

## Week 7-8: Essential Reports & Exports

### Overview

Implement coverage reports, fairness dashboards, and PDF/Excel export functionality.

### Technical Specifications

#### 1. Report Views

**File:** `team_planner/reports/views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from ..permissions import HasRolePermission
from team_planner.shifts.models import Shift
from team_planner.employees.models import EmployeeProfile


class ReportViewSet(viewsets.ViewSet):
    """Generate various reports."""
    
    permission_classes = [IsAuthenticated, HasRolePermission]
    permission_required = 'can_view_reports'
    
    @action(detail=False, methods=['get'])
    def coverage_summary(self, request):
        """Get shift coverage summary for a date range."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        team_id = request.query_params.get('team_id')
        
        # Build query
        queryset = Shift.objects.filter(
            date__range=[start_date, end_date]
        )
        
        if team_id:
            queryset = queryset.filter(shift_template__team_id=team_id)
        
        # Calculate coverage metrics
        total_shifts = queryset.count()
        filled_shifts = queryset.filter(assigned_employee__isnull=False).count()
        coverage_rate = (filled_shifts / total_shifts * 100) if total_shifts > 0 else 0
        
        # Group by date
        daily_coverage = queryset.values('date').annotate(
            total=Count('id'),
            filled=Count('assigned_employee'),
            open=Count('id', filter=Q(assigned_employee__isnull=True))
        ).order_by('date')
        
        return Response({
            'summary': {
                'total_shifts': total_shifts,
                'filled_shifts': filled_shifts,
                'open_shifts': total_shifts - filled_shifts,
                'coverage_rate': round(coverage_rate, 2)
            },
            'daily': list(daily_coverage)
        })
    
    @action(detail=False, methods=['get'])
    def fairness_dashboard(self, request):
        """Get fairness metrics for team members."""
        team_id = request.query_params.get('team_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Get employee metrics
        employees = EmployeeProfile.objects.filter(
            teams__id=team_id
        ).annotate(
            total_hours=Sum(
                'shifts__actual_hours',
                filter=Q(
                    shifts__date__range=[start_date, end_date],
                    shifts__status='completed'
                )
            ),
            shift_count=Count(
                'shifts',
                filter=Q(shifts__date__range=[start_date, end_date])
            ),
            weekend_shifts=Count(
                'shifts',
                filter=Q(
                    shifts__date__range=[start_date, end_date],
                    shifts__date__week_day__in=[1, 7]  # Sunday=1, Saturday=7
                )
            )
        )
        
        data = []
        for emp in employees:
            data.append({
                'employee_id': emp.id,
                'name': emp.user.get_full_name(),
                'total_hours': float(emp.total_hours or 0),
                'shift_count': emp.shift_count,
                'weekend_shifts': emp.weekend_shifts,
                'avg_hours_per_shift': (
                    float(emp.total_hours / emp.shift_count)
                    if emp.shift_count > 0 else 0
                )
            })
        
        # Calculate team averages
        if data:
            avg_hours = sum(e['total_hours'] for e in data) / len(data)
            avg_shifts = sum(e['shift_count'] for e in data) / len(data)
        else:
            avg_hours = 0
            avg_shifts = 0
        
        return Response({
            'employees': data,
            'team_average': {
                'hours': round(avg_hours, 2),
                'shifts': round(avg_shifts, 2)
            }
        })
```

#### 2. Export Service

**File:** `team_planner/reports/export_service.py`

```python
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse


class ExportService:
    """Service for exporting data to various formats."""
    
    @staticmethod
    def export_schedule_to_excel(shifts, filename="schedule.xlsx"):
        """Export schedule to Excel."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Schedule"
        
        # Headers
        headers = ['Date', 'Shift', 'Employee', 'Start Time', 'End Time', 'Hours', 'Status']
        ws.append(headers)
        
        # Style headers
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        
        # Data rows
        for shift in shifts:
            ws.append([
                shift.date.strftime('%Y-%m-%d'),
                shift.shift_template.name,
                shift.assigned_employee.user.get_full_name() if shift.assigned_employee else 'Unassigned',
                shift.start_time.strftime('%H:%M'),
                shift.end_time.strftime('%H:%M'),
                float(shift.actual_hours or 0),
                shift.get_status_display()
            ])
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Create response
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @staticmethod
    def export_schedule_to_pdf(shifts, title="Schedule", filename="schedule.pdf"):
        """Export schedule to PDF."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        
        # Title
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))
        
        # Build table data
        data = [['Date', 'Shift', 'Employee', 'Time', 'Hours']]
        
        for shift in shifts:
            data.append([
                shift.date.strftime('%Y-%m-%d'),
                shift.shift_template.name,
                shift.assigned_employee.user.get_full_name() if shift.assigned_employee else 'Unassigned',
                f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}",
                f"{shift.actual_hours or 0:.1f}h"
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        # Create response
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
```

### Testing Checklist

- [ ] Coverage reports accurate
- [ ] Fairness metrics correct
- [ ] Excel export works
- [ ] PDF export works
- [ ] Charts render correctly
- [ ] Permissions enforced

### Estimated Effort

- Backend development: 4 days
- Export functionality: 2 days
- Frontend dashboards: 3 days
- Testing: 1 day
- **Total: 10 days (2 weeks)**

---

## Week 9-10: Testing & Deployment

### Testing Strategy

#### 1. Unit Tests

**Coverage targets:**
- Models: 95%+
- Services: 90%+
- Views/APIs: 85%+
- Utilities: 90%+

#### 2. Integration Tests

**Critical flows:**
- [ ] User registration → MFA setup → Login
- [ ] Shift assignment → Notification delivery
- [ ] Swap request → Approval → Notification
- [ ] Leave request → Approval → Schedule update
- [ ] Role assignment → Permission enforcement

#### 3. End-to-End Tests

**Using Cypress/Playwright:**
- [ ] Complete user journey flows
- [ ] Cross-browser compatibility
- [ ] Mobile responsiveness
- [ ] Real-time notifications
- [ ] Export functionality

#### 4. Security Testing

- [ ] MFA bypass attempts
- [ ] Permission escalation attempts
- [ ] SQL injection tests
- [ ] XSS vulnerability tests
- [ ] CSRF protection
- [ ] Rate limiting

#### 5. Performance Testing

- [ ] Load test (100 concurrent users)
- [ ] WebSocket stress test
- [ ] Database query optimization
- [ ] API response times < 200ms
- [ ] Frontend bundle size < 500KB

### Deployment Checklist

#### Pre-Deployment

- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Database backup created
- [ ] Migration scripts tested
- [ ] Environment variables configured
- [ ] SSL certificates valid
- [ ] Monitoring configured

#### Deployment Steps

1. **Database Migration**
   ```bash
   python manage.py migrate --plan
   python manage.py migrate
   python manage.py setup_roles
   ```

2. **Static Files**
   ```bash
   cd frontend && npm run build
   python manage.py collectstatic --noinput
   ```

3. **Dependencies**
   ```bash
   pip install -r requirements/production.txt
   ```

4. **Services**
   ```bash
   systemctl restart team-planner
   systemctl restart celery
   systemctl restart redis
   ```

5. **Verification**
   - [ ] Health check endpoint responds
   - [ ] WebSocket connections work
   - [ ] Email sending functional
   - [ ] Cron jobs scheduled
   - [ ] Logs accessible

#### Post-Deployment

- [ ] Smoke tests pass
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Verify backups running
- [ ] Update status page
- [ ] Notify stakeholders

### Rollback Plan

```bash
# If issues detected
git checkout <previous-tag>
python manage.py migrate <app_name> <previous_migration>
systemctl restart team-planner
```

### Estimated Effort

- Unit testing: 3 days
- Integration testing: 2 days
- E2E testing: 2 days
- Security testing: 1 day
- Performance tuning: 1 day
- Deployment: 1 day
- **Total: 10 days (2 weeks)**

---

## Budget Breakdown

### Development Costs (8-10 weeks)

| Phase | Duration | Cost (@ $500/day) |
|-------|----------|-------------------|
| MFA Implementation | 1.5 weeks | $3,750 |
| RBAC System | 2 weeks | $5,000 |
| Notification System | 2.5 weeks | $6,250 |
| Reports & Exports | 2 weeks | $5,000 |
| Testing & QA | 2 weeks | $5,000 |
| **Total** | **10 weeks** | **$25,000** |

### Additional Costs

| Item | Cost |
|------|------|
| DevOps/Infrastructure | $2,000 |
| Third-party services (Twilio, etc.) | $500/month |
| SSL certificates | $200/year |
| Monitoring tools | $100/month |
| Documentation | $1,000 |
| **Subtotal** | **$3,700** |

### Contingency Buffer (20%)

| Item | Cost |
|------|------|
| Unexpected issues | $5,000 |
| Additional testing | $2,000 |
| **Subtotal** | **$7,000** |

### **Grand Total: $35,700**

Within the $40,000-$50,000 budget range ✅

---

## Success Metrics

### Week 2
- ✅ MFA enabled for all users
- ✅ 100% of staff using MFA

### Week 4
- ✅ Role system implemented
- ✅ All permissions enforced
- ✅ Audit logging active

### Week 6
- ✅ Real-time notifications working
- ✅ 90%+ notification delivery rate
- ✅ Email templates deployed

### Week 8
- ✅ Reports accessible
- ✅ Export functionality working
- ✅ Performance targets met

### Week 10
- ✅ All tests passing
- ✅ Production deployment successful
- ✅ Zero critical bugs

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| WebSocket scaling issues | Medium | High | Use Redis adapter, load testing |
| Email deliverability | Low | Medium | Configure SPF/DKIM, use SendGrid |
| SMS costs exceed budget | Medium | Low | Start email-only, add SMS later |
| Performance degradation | Medium | High | Database indexing, caching, monitoring |
| Security vulnerabilities | Low | High | Security audit, penetration testing |

---

## Next Steps

1. **Approve plan** and budget allocation
2. **Assign development team** (2 developers + 1 QA)
3. **Set up project tracking** (Jira/Linear)
4. **Create development branch** (`feature/phase-1-security`)
5. **Begin Week 1** - MFA implementation

---

**Document Version:** 1.0  
**Last Updated:** October 1, 2025  
**Next Review:** Weekly during implementation
