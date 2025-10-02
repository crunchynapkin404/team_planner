"""Custom authentication views with MFA support."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from team_planner.users.models import TwoFactorDevice


@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_mfa_check(request):
    """
    Login endpoint that checks for MFA requirement.
    
    If MFA is enabled for the user, returns mfa_required=True
    and stores user info in session for later verification.
    
    If MFA is not enabled, returns auth token immediately.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Authenticate user
    user = authenticate(username=username, password=password)
    
    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check if user has MFA enabled
    try:
        mfa_device = user.mfa_device
        if mfa_device.is_verified:
            # MFA is enabled - don't issue token yet
            # Store user ID in session for MFA verification
            request.session['mfa_user_id'] = user.id
            request.session['mfa_username'] = user.username
            
            return Response({
                'mfa_required': True,
                'message': 'Please enter your MFA token',
                'user_id': user.id,
                'username': user.username
            })
    except TwoFactorDevice.DoesNotExist:
        # MFA not enabled
        pass
    
    # MFA not enabled or not verified - issue token immediately
    token, _ = Token.objects.get_or_create(user=user)
    
    return Response({
        'mfa_required': False,
        'token': token.key,
        'user_id': user.id,
        'username': user.username
    })
