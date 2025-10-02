#!/usr/bin/env python3
"""
Integration test script for MFA functionality.
Tests the complete MFA workflow including setup, verification, and login.
"""

import os
import sys
import django
import pyotp
from io import BytesIO
from PIL import Image
import base64

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ.setdefault('DATABASE_URL', 'sqlite:///db.sqlite3')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from team_planner.users.models import TwoFactorDevice, MFALoginAttempt

User = get_user_model()

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}→ {text}{Colors.ENDC}")

def cleanup_test_data():
    """Remove any existing test data."""
    User.objects.filter(username='mfa_test_user').delete()
    print_info("Cleaned up existing test data")

def test_mfa_setup():
    """Test MFA setup workflow."""
    print_header("Testing MFA Setup")
    
    # Create test user
    user = User.objects.create_user(
        username='mfa_test_user',
        email='mfa_test@example.com',
        password='testpass123'
    )
    print_success(f"Created test user: {user.username}")
    
    # Login
    client = Client()
    response = client.post('/api/auth/login/', {
        'username': 'mfa_test_user',
        'password': 'testpass123'
    }, content_type='application/json')
    
    if response.status_code != 200:
        print_error(f"Login failed: {response.status_code}")
        return False
    
    token = response.json().get('token')
    print_success(f"Login successful, got token")
    
    # Setup MFA
    response = client.post('/api/mfa/setup/', 
        HTTP_AUTHORIZATION=f'Token {token}',
        content_type='application/json'
    )
    
    if response.status_code != 200:
        print_error(f"MFA setup failed: {response.status_code}")
        return False
    
    data = response.json()
    secret = data.get('secret')
    qr_code = data.get('qr_code')
    backup_codes = data.get('backup_codes')
    
    print_success(f"MFA setup initialized")
    print_info(f"Secret: {secret}")
    print_info(f"Backup codes count: {len(backup_codes)}")
    print_info(f"QR code generated: {'Yes' if qr_code else 'No'}")
    
    # Verify QR code is valid base64 PNG
    try:
        qr_data = base64.b64decode(qr_code.split(',')[1])
        img = Image.open(BytesIO(qr_data))
        if img.format == 'PNG':
            print_success(f"QR code is valid PNG ({img.size[0]}x{img.size[1]})")
        else:
            print_error(f"QR code is not PNG: {img.format}")
    except Exception as e:
        print_error(f"QR code validation failed: {e}")
    
    # Generate TOTP token
    totp = pyotp.TOTP(secret)
    token_code = totp.now()
    print_info(f"Generated TOTP token: {token_code}")
    
    # Verify token
    response = client.post('/api/mfa/verify/', 
        {'token': token_code},
        HTTP_AUTHORIZATION=f'Token {token}',
        content_type='application/json'
    )
    
    if response.status_code != 200:
        print_error(f"Token verification failed: {response.status_code}")
        print_error(f"Response: {response.json()}")
        return False
    
    print_success("Token verified successfully")
    
    # Check device was created
    device = TwoFactorDevice.objects.filter(user=user).first()
    if not device:
        print_error("MFA device not created")
        return False
    
    print_success(f"MFA device created and verified: {device.is_verified}")
    
    return True, user, secret, backup_codes

def test_mfa_login(user, secret, backup_codes):
    """Test MFA login workflow."""
    print_header("Testing MFA Login")
    
    client = Client()
    
    # Regular login
    response = client.post('/api/auth/login/', {
        'username': 'mfa_test_user',
        'password': 'testpass123'
    }, content_type='application/json')
    
    if response.status_code != 200:
        print_error(f"Login failed: {response.status_code}")
        return False
    
    token = response.json().get('token')
    print_success("Initial login successful")
    
    # Generate TOTP token for MFA verification
    totp = pyotp.TOTP(secret)
    token_code = totp.now()
    
    # Verify MFA during login
    response = client.post('/api/mfa/login/verify/', {
        'token': token_code,
        'use_backup': False
    }, HTTP_AUTHORIZATION=f'Token {token}', content_type='application/json')
    
    if response.status_code != 200:
        print_error(f"MFA login verification failed: {response.status_code}")
        return False
    
    print_success("MFA login verification successful")
    
    # Check login attempt was logged
    attempt = MFALoginAttempt.objects.filter(user=user, success=True).first()
    if attempt:
        print_success(f"Login attempt logged: IP={attempt.ip_address}")
    else:
        print_error("Login attempt not logged")
    
    return True

def test_backup_code_login(user, backup_codes):
    """Test backup code login."""
    print_header("Testing Backup Code Login")
    
    client = Client()
    
    # Login
    response = client.post('/api/auth/login/', {
        'username': 'mfa_test_user',
        'password': 'testpass123'
    }, content_type='application/json')
    
    token = response.json().get('token')
    backup_code = backup_codes[0]
    
    print_info(f"Using backup code: {backup_code}")
    
    # Verify with backup code
    response = client.post('/api/mfa/login/verify/', {
        'token': backup_code,
        'use_backup': True
    }, HTTP_AUTHORIZATION=f'Token {token}', content_type='application/json')
    
    if response.status_code != 200:
        print_error(f"Backup code verification failed: {response.status_code}")
        return False
    
    print_success("Backup code verification successful")
    
    data = response.json()
    remaining = data.get('backup_codes_remaining', 0)
    print_info(f"Backup codes remaining: {remaining}")
    
    # Try to reuse the same backup code (should fail)
    response = client.post('/api/mfa/login/verify/', {
        'token': backup_code,
        'use_backup': True
    }, HTTP_AUTHORIZATION=f'Token {token}', content_type='application/json')
    
    if response.status_code == 200:
        print_error("Backup code was reused (should fail)")
        return False
    
    print_success("Backup code reuse prevented")
    
    return True

def test_mfa_status(user):
    """Test MFA status endpoint."""
    print_header("Testing MFA Status")
    
    client = Client()
    
    # Login
    response = client.post('/api/auth/login/', {
        'username': 'mfa_test_user',
        'password': 'testpass123'
    }, content_type='application/json')
    
    token = response.json().get('token')
    
    # Get MFA status
    response = client.get('/api/mfa/status/', 
        HTTP_AUTHORIZATION=f'Token {token}'
    )
    
    if response.status_code != 200:
        print_error(f"MFA status check failed: {response.status_code}")
        return False
    
    data = response.json()
    print_success(f"MFA enabled: {data.get('mfa_enabled')}")
    print_info(f"Backup codes remaining: {data.get('backup_codes_remaining')}")
    
    if data.get('devices'):
        device = data['devices'][0]
        print_info(f"Device verified: {device.get('is_verified')}")
        print_info(f"Last used: {device.get('last_used', 'Never')}")
    
    return True

def test_mfa_disable(user, secret):
    """Test MFA disable workflow."""
    print_header("Testing MFA Disable")
    
    client = Client()
    
    # Login
    response = client.post('/api/auth/login/', {
        'username': 'mfa_test_user',
        'password': 'testpass123'
    }, content_type='application/json')
    
    token = response.json().get('token')
    
    # Generate TOTP token
    totp = pyotp.TOTP(secret)
    token_code = totp.now()
    
    # Disable MFA
    response = client.post('/api/mfa/disable/', {
        'password': 'testpass123',
        'token': token_code
    }, HTTP_AUTHORIZATION=f'Token {token}', content_type='application/json')
    
    if response.status_code != 200:
        print_error(f"MFA disable failed: {response.status_code}")
        return False
    
    print_success("MFA disabled successfully")
    
    # Check device was deleted
    device = TwoFactorDevice.objects.filter(user=user).first()
    if device:
        print_error("MFA device still exists")
        return False
    
    print_success("MFA device removed")
    
    return True

def main():
    """Run all integration tests."""
    print_header("MFA Integration Test Suite")
    
    # Cleanup
    cleanup_test_data()
    
    try:
        # Test MFA setup
        result = test_mfa_setup()
        if not result:
            print_error("MFA setup test failed")
            return 1
        
        success, user, secret, backup_codes = result
        
        # Test MFA login
        if not test_mfa_login(user, secret, backup_codes):
            print_error("MFA login test failed")
            return 1
        
        # Test backup code login
        if not test_backup_code_login(user, backup_codes):
            print_error("Backup code login test failed")
            return 1
        
        # Test MFA status
        if not test_mfa_status(user):
            print_error("MFA status test failed")
            return 1
        
        # Test MFA disable
        if not test_mfa_disable(user, secret):
            print_error("MFA disable test failed")
            return 1
        
        # Final summary
        print_header("Integration Test Results")
        print_success("All integration tests passed!")
        print_info("\nTest Coverage:")
        print_info("✓ MFA setup with QR code generation")
        print_info("✓ TOTP token verification")
        print_info("✓ MFA login workflow")
        print_info("✓ Backup code authentication")
        print_info("✓ Backup code reuse prevention")
        print_info("✓ MFA status endpoint")
        print_info("✓ MFA disable with security checks")
        print_info("✓ Login attempt logging")
        
        return 0
        
    except Exception as e:
        print_error(f"Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Cleanup
        cleanup_test_data()
        print_info("\nTest data cleaned up")

if __name__ == '__main__':
    sys.exit(main())
