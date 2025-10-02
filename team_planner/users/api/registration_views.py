"""User registration views with admin verification."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from ..permissions import check_user_permission

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user account.
    User will be inactive until admin approval.
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
    
    # Password strength check
    if len(password) < 8:
        return Response(
            {'error': 'Password must be at least 8 characters long'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check for existing username
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check for existing email
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already registered'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Create user (inactive until admin approves)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            name=name,
            is_active=False,
            role='employee'  # Default role
        )
        
        return Response({
            'success': True,
            'message': 'Registration successful. Your account is pending admin approval. You will be able to log in once approved.',
            'user_id': user.id,
            'requires_approval': True
        })
    
    except Exception as e:
        return Response(
            {'error': f'Registration failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_users(request):
    """Get list of users pending admin approval."""
    # Check if user has permission to manage users
    if not check_user_permission(request.user, 'can_manage_users'):
        return Response(
            {'error': 'Permission denied. Only admins can view pending users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get all inactive users (pending approval)
    pending = User.objects.filter(is_active=False).values(
        'id', 'username', 'email', 'name', 'date_joined'
    )
    
    return Response({
        'success': True,
        'pending_users': list(pending),
        'count': len(pending)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_user(request, user_id):
    """Approve a pending user registration."""
    # Check if user has permission to manage users
    if not check_user_permission(request.user, 'can_manage_users'):
        return Response(
            {'error': 'Permission denied. Only admins can approve users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id, is_active=False)
    except User.DoesNotExist:
        return Response(
            {'error': 'Pending user not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Activate user
    user.is_active = True
    user.save()
    
    return Response({
        'success': True,
        'message': f'User {user.username} has been approved and can now log in.',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'name': user.name
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_user(request, user_id):
    """Reject and delete a pending user registration."""
    # Check if user has permission to manage users
    if not check_user_permission(request.user, 'can_manage_users'):
        return Response(
            {'error': 'Permission denied. Only admins can reject users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id, is_active=False)
    except User.DoesNotExist:
        return Response(
            {'error': 'Pending user not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    username = user.username
    user.delete()
    
    return Response({
        'success': True,
        'message': f'User {username} registration has been rejected and deleted.'
    })
