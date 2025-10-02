"""MFA (Multi-Factor Authentication) API views."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from ..models import TwoFactorDevice, MFALoginAttempt

User = get_user_model()


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


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
@permission_classes([AllowAny])
def mfa_login_verify(request):
    """
    Verify MFA token during login.
    Used after initial username/password authentication.
    """
    from rest_framework.authtoken.models import Token
    
    # Try to get user_id from session first, then from request body
    user_id = request.session.get('mfa_user_id') or request.data.get('user_id')
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
            
            # Clear session if it exists
            if 'mfa_user_id' in request.session:
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
