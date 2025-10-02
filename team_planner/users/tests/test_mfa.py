"""Tests for MFA (Multi-Factor Authentication) functionality."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from team_planner.users.models import TwoFactorDevice, MFALoginAttempt
import pyotp

User = get_user_model()


@pytest.mark.django_db
class TestTwoFactorDevice:
    """Test TwoFactorDevice model functionality."""
    
    def test_create_device(self):
        """Test creating a TwoFactorDevice."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        device = TwoFactorDevice.objects.create(user=user)
        
        assert device.user == user
        assert device.is_verified is False
        assert device.secret_key == ''
        assert device.backup_codes == []
        assert device.device_name == 'Authenticator App'
    
    def test_generate_secret(self):
        """Test secret key generation."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        
        secret = device.generate_secret()
        
        assert len(secret) == 32
        assert secret.isalnum()
        assert secret.isupper()
        assert device.secret_key == secret
    
    def test_verify_token_success(self):
        """Test TOTP token verification with valid token."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        device.generate_secret()
        
        # Get current token
        totp = device.get_totp()
        token = totp.now()
        
        # Should verify successfully
        assert device.verify_token(token) is True
    
    def test_verify_token_failure(self):
        """Test TOTP token verification with invalid token."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        device.generate_secret()
        
        # Invalid token
        assert device.verify_token('000000') is False
        assert device.verify_token('123456') is False
    
    def test_backup_codes_generation(self):
        """Test backup code generation."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        
        codes = device.generate_backup_codes(count=10)
        
        assert len(codes) == 10
        assert all(len(code) == 8 for code in codes)
        assert all(code.isupper() for code in codes)
        assert len(set(codes)) == 10  # All unique
        assert device.backup_codes == codes
    
    def test_verify_backup_code_success(self):
        """Test backup code verification and consumption."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        codes = device.generate_backup_codes(count=10)
        device.save()
        
        # Verify first code
        code = codes[0]
        assert device.verify_backup_code(code) is True
        
        # Code should be removed after use
        device.refresh_from_db()
        assert code not in device.backup_codes
        assert len(device.backup_codes) == 9
    
    def test_verify_backup_code_reuse_prevented(self):
        """Test that backup codes can't be reused."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        codes = device.generate_backup_codes(count=10)
        device.save()
        
        code = codes[0]
        
        # First use succeeds
        assert device.verify_backup_code(code) is True
        
        # Second use fails
        device.refresh_from_db()
        assert device.verify_backup_code(code) is False
    
    def test_qr_code_generation(self):
        """Test QR code generation."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com'
        )
        device = TwoFactorDevice.objects.create(user=user)
        device.generate_secret()
        
        qr_code = device.get_qr_code()
        
        assert qr_code.startswith('data:image/png;base64,')
        assert len(qr_code) > 100  # Should be a substantial base64 string
    
    def test_one_device_per_user(self):
        """Test OneToOne relationship - one device per user."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device1 = TwoFactorDevice.objects.create(user=user)
        
        # Creating another device should replace the first
        with pytest.raises(Exception):
            TwoFactorDevice.objects.create(user=user)


@pytest.mark.django_db
class TestMFALoginAttempt:
    """Test MFALoginAttempt model functionality."""
    
    def test_create_login_attempt(self):
        """Test creating a login attempt record."""
        user = User.objects.create_user(username='test', email='test@example.com')
        
        attempt = MFALoginAttempt.objects.create(
            user=user,
            success=True,
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0'
        )
        
        assert attempt.user == user
        assert attempt.success is True
        assert attempt.ip_address == '192.168.1.1'
        assert attempt.user_agent == 'Mozilla/5.0'
        assert attempt.failure_reason == ''
    
    def test_failed_attempt_tracking(self):
        """Test tracking failed login attempts."""
        user = User.objects.create_user(username='test', email='test@example.com')
        
        attempt = MFALoginAttempt.objects.create(
            user=user,
            success=False,
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            failure_reason='invalid_token'
        )
        
        assert attempt.success is False
        assert attempt.failure_reason == 'invalid_token'
    
    def test_attempt_ordering(self):
        """Test that attempts are ordered by creation date (newest first)."""
        user = User.objects.create_user(username='test', email='test@example.com')
        
        # Create multiple attempts
        attempt1 = MFALoginAttempt.objects.create(
            user=user, success=True, ip_address='192.168.1.1'
        )
        attempt2 = MFALoginAttempt.objects.create(
            user=user, success=False, ip_address='192.168.1.2'
        )
        attempt3 = MFALoginAttempt.objects.create(
            user=user, success=True, ip_address='192.168.1.3'
        )
        
        attempts = MFALoginAttempt.objects.filter(user=user)
        
        assert attempts[0] == attempt3  # Newest first
        assert attempts[1] == attempt2
        assert attempts[2] == attempt1


@pytest.mark.django_db
class TestUserRoleField:
    """Test User model role field."""
    
    def test_default_role(self):
        """Test that new users get default employee role."""
        user = User.objects.create_user(
            username='test',
            email='test@example.com'
        )
        
        assert user.role == 'employee'
    
    def test_set_custom_role(self):
        """Test setting custom roles."""
        user = User.objects.create_user(
            username='manager',
            email='manager@example.com'
        )
        user.role = 'manager'
        user.save()
        
        user.refresh_from_db()
        assert user.role == 'manager'
    
    def test_mfa_required_field(self):
        """Test MFA required field."""
        user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            is_staff=True
        )
        
        assert user.mfa_required is False
        
        user.mfa_required = True
        user.save()
        
        user.refresh_from_db()
        assert user.mfa_required is True


@pytest.mark.django_db
class TestMFAWorkflow:
    """Integration tests for complete MFA workflow."""
    
    def test_complete_mfa_setup_workflow(self):
        """Test complete MFA setup and verification workflow."""
        # 1. Create user
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='testpass123'
        )
        
        # 2. Create device and generate secret
        device = TwoFactorDevice.objects.create(user=user)
        device.generate_secret()
        device.generate_backup_codes()
        device.save()
        
        assert device.is_verified is False
        assert len(device.backup_codes) == 10
        
        # 3. Verify with token
        totp = device.get_totp()
        token = totp.now()
        
        assert device.verify_token(token) is True
        
        # 4. Mark as verified
        device.is_verified = True
        device.last_used = timezone.now()
        device.save()
        
        device.refresh_from_db()
        assert device.is_verified is True
        assert device.last_used is not None
    
    def test_mfa_disable_workflow(self):
        """Test MFA disable workflow."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        device.generate_secret()
        device.is_verified = True
        device.save()
        
        # Verify token before disabling
        totp = device.get_totp()
        token = totp.now()
        assert device.verify_token(token) is True
        
        # Delete device (disable MFA)
        device.delete()
        
        # Device should be gone
        assert not TwoFactorDevice.objects.filter(user=user).exists()
    
    def test_backup_code_recovery_workflow(self):
        """Test account recovery with backup codes."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        device.generate_secret()
        codes = device.generate_backup_codes()
        device.is_verified = True
        device.save()
        
        # User loses device, uses backup code
        backup_code = codes[0]
        assert device.verify_backup_code(backup_code) is True
        
        # Backup code is consumed
        device.refresh_from_db()
        assert backup_code not in device.backup_codes
        assert len(device.backup_codes) == 9
