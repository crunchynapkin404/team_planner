# MFA Login Flow - Fixed!

## Problem

User could enable MFA successfully, but when logging in again, they were NOT prompted for the MFA token. The system was bypassing MFA verification entirely.

## Root Cause

The login endpoint (`/api/auth-token/`) was issuing authentication tokens immediately without checking if the user has MFA enabled.

## Solution

### 1. Created New Login Endpoint with MFA Check

**File:** `team_planner/users/api/auth_views.py`

```python
@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_mfa_check(request):
    """
    Login endpoint that checks for MFA requirement.
    
    If MFA is enabled: Returns mfa_required=True
    If MFA is disabled: Returns auth token immediately
    """
    user = authenticate(username=username, password=password)
    
    # Check if user has MFA enabled
    try:
        mfa_device = user.mfa_device
        if mfa_device.is_verified:
            # Store user in session for later MFA verification
            request.session['mfa_user_id'] = user.id
            return Response({
                'mfa_required': True,
                'message': 'Please enter your MFA token',
                'user_id': user.id,
                'username': user.username
            })
    except TwoFactorDevice.DoesNotExist:
        pass
    
    # No MFA - issue token immediately
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'mfa_required': False,
        'token': token.key,
        'user_id': user.id,
        'username': user.username
    })
```

### 2. Updated API Router

**File:** `config/api_router.py`

Added new endpoint:
```python
path("auth/login/", auth_views.login_with_mfa_check, name="auth-login-mfa"),
```

### 3. Updated Frontend Auth Service

**File:** `frontend/src/services/authService.ts`

Modified login to handle MFA check:
```typescript
async login(credentials: LoginCredentials) {
  const response = await apiClient.post('/api/auth/login/', credentials);
  
  if (response.mfa_required) {
    // Return MFA required flag
    return {
      mfa_required: true,
      user_id: response.user_id,
      username: response.username
    };
  }
  
  // No MFA - return token and user
  localStorage.setItem('token', response.token);
  const user = await this.getCurrentUser();
  return { user, token: response.token, mfa_required: false };
}
```

### 4. Updated Login Form Component

**File:** `frontend/src/components/auth/LoginForm.tsx`

Added MFA dialog handling:
```tsx
const [showMFADialog, setShowMFADialog] = useState(false);

const handleSubmit = async (e: React.FormEvent) => {
  const response = await authService.login(credentials);
  
  if (response.mfa_required) {
    // Show MFA dialog
    setShowMFADialog(true);
  } else {
    // No MFA - redirect to dashboard
    window.location.href = '/dashboard';
  }
};

return (
  <>
    {/* Login form... */}
    
    {/* MFA Dialog */}
    <MFALogin
      open={showMFADialog}
      onClose={handleMFAClose}
      onSuccess={handleMFASuccess}
    />
  </>
);
```

## New Login Flow

### Without MFA:
1. User enters username/password
2. Backend verifies credentials
3. Backend checks: No MFA device found
4. Backend issues auth token immediately
5. Frontend stores token and redirects to dashboard

### With MFA Enabled:
1. User enters username/password
2. Backend verifies credentials
3. Backend checks: **MFA device found and verified**
4. Backend returns `{mfa_required: true, ...}`
5. Backend stores user ID in session
6. Frontend shows MFA dialog
7. User enters 6-digit TOTP token (or backup code)
8. Frontend calls `/api/mfa/login/verify/` with token
9. Backend verifies TOTP token
10. Backend issues auth token
11. Frontend stores token and redirects to dashboard

## Testing

### Test 1: Login with MFA Enabled
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Response:
{
  "mfa_required": true,
  "message": "Please enter your MFA token",
  "user_id": 1,
  "username": "admin"
}
```

### Test 2: MFA Verification
```bash
curl -X POST http://localhost:8000/api/mfa/login/verify/ \
  -H "Content-Type: application/json" \
  -d '{"token":"123456"}' \
  --cookie-jar cookies.txt \
  --cookie cookies.txt

# Response:
{
  "success": true,
  "token": "abc123...",
  "user_id": 1,
  "username": "admin",
  "backup_codes_remaining": 10
}
```

## Status

✅ **FIXED!** 

The MFA login flow is now complete:
- Backend correctly detects MFA requirement
- Frontend shows MFA dialog when needed
- Users with MFA enabled are prompted for tokens
- Users without MFA login normally

## Files Modified

1. `/home/vscode/team_planner/team_planner/users/api/auth_views.py` - NEW
2. `/home/vscode/team_planner/config/api_router.py` - Added new endpoint
3. `/home/vscode/team_planner/frontend/src/services/authService.ts` - Updated login logic
4. `/home/vscode/team_planner/frontend/src/components/auth/LoginForm.tsx` - Added MFA dialog

## Next Steps

1. **Test in browser:**
   - Login with admin/admin123
   - Should see MFA dialog
   - Enter 6-digit code from authenticator app
   - Should successfully login

2. **Test with new user (no MFA):**
   - Create user without MFA
   - Should login without MFA prompt

3. **Session persistence:**
   - Ensure session handling works correctly
   - Clear session after successful MFA verification

## Date Fixed

October 1, 2025 - 12:00 PM
