# Next Steps Roadmap - After RBAC Phase 2

**Date:** October 1, 2025  
**Current Status:** ✅ MFA Complete, ✅ RBAC Complete, ✅ Unified Management Complete

---

## 📍 Where We Are Now

### ✅ Completed (Weeks 1-4)
- **Week 1-2**: Multi-Factor Authentication (MFA) system
  - TOTP-based 2FA with QR codes
  - Backup codes system
  - Frontend integration complete
  - 18 unit tests passing

- **Week 2.5**: User Registration & Admin Approval
  - New user registration flow
  - Admin approval workflow
  - Email verification system

- **Week 3-4**: Role-Based Access Control (RBAC)
  - 5 roles: Super Admin, Manager, Shift Planner, Employee, Read-Only
  - 22 permissions covering all features
  - Backend permission system complete
  - Frontend permission gates implemented

- **Week 4+**: RBAC Frontend Integration
  - Unified Management Console (3-in-1 page)
  - Permission-based navigation
  - Permission-protected features (Calendar, Swaps, Leaves, Orchestrator)
  - Department management added

### 🔄 Current State
- **Backend**: Fully functional with RBAC but not enforced on views yet
- **Frontend**: Permission-based UI rendering working
- **Docker**: Both containers running (django:8000, frontend:3000)
- **Database**: 5 users, 5 roles, 22 permissions configured
- **Port**: Successfully migrated from 3001 to 3000

---

## 🎯 IMMEDIATE NEXT STEPS (Week 5-6: Notification System)

### Priority 1: Backend Permission Enforcement ⭐⭐⭐
**Current State**: Frontend hides features, but API endpoints are still open  
**Risk**: Security vulnerability - unauthorized users can still call APIs directly

**Implementation Steps:**

#### 1. Create Permission Decorators
**File**: `team_planner/rbac/decorators.py`

```python
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .services import RBACService

def require_permission(permission_name):
    """Decorator to require a specific permission."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            rbac_service = RBACService()
            if not rbac_service.has_permission(request.user, permission_name):
                return Response(
                    {'error': f'Permission denied: {permission_name} required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

#### 2. Apply to Shift Views
**File**: `team_planner/shifts/api.py`

```python
from team_planner.rbac.decorators import require_permission

class ShiftViewSet(viewsets.ModelViewSet):
    
    @require_permission('can_view_schedule')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @require_permission('can_create_shift')
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @require_permission('can_edit_shift')
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
```

#### 3. Apply to Swap Views
**File**: `team_planner/shifts/api.py` (SwapRequestViewSet)

```python
@require_permission('can_request_swap')
def create(self, request, *args, **kwargs):
    return super().create(request, *args, **kwargs)

@require_permission('can_approve_swap')
@action(detail=True, methods=['post'])
def approve(self, request, pk=None):
    # approval logic
```

#### 4. Apply to Leave Views
**File**: `team_planner/leaves/api.py`

```python
@require_permission('can_request_leave')
def create(self, request, *args, **kwargs):
    return super().create(request, *args, **kwargs)

@require_permission('can_approve_leave')
@action(detail=True, methods=['post'])
def approve(self, request, pk=None):
    # approval logic
```

#### 5. Apply to Orchestrator Views
**File**: `team_planner/orchestrators/api.py`

```python
@require_permission('can_run_orchestrator')
def create(self, request, *args, **kwargs):
    return super().create(request, *args, **kwargs)
```

**Estimated Time**: 4-6 hours  
**Priority**: HIGH (Security)

---

### Priority 2: Notification System Foundation ⭐⭐⭐
**Scope**: Week 5-6 of the original plan  
**Goal**: Email notifications for key events

#### Phase 1: Email Configuration (Day 1)

**1. Install Dependencies**
```bash
pip install django-anymail[sendgrid]  # or mailgun, ses, etc.
```

**2. Configure Email Backend**
**File**: `config/settings/base.py`

```python
# Email Configuration
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'  # Dev: print to console
)
EMAIL_HOST = env('EMAIL_HOST', default='smtp.sendgrid.net')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@teamplanner.com')
```

**3. Create Notification Models**
**File**: `team_planner/notifications/models.py`

```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationType(models.TextChoices):
    SHIFT_ASSIGNED = 'shift_assigned', 'Shift Assigned'
    SHIFT_CHANGED = 'shift_changed', 'Shift Changed'
    SHIFT_CANCELLED = 'shift_cancelled', 'Shift Cancelled'
    SWAP_REQUEST = 'swap_request', 'Swap Request'
    SWAP_APPROVED = 'swap_approved', 'Swap Approved'
    SWAP_REJECTED = 'swap_rejected', 'Swap Rejected'
    LEAVE_APPROVED = 'leave_approved', 'Leave Approved'
    LEAVE_REJECTED = 'leave_rejected', 'Leave Rejected'
    SCHEDULE_PUBLISHED = 'schedule_published', 'Schedule Published'

class NotificationPreference(models.Model):
    """User preferences for notifications."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Email preferences
    email_shift_assigned = models.BooleanField(default=True)
    email_shift_changed = models.BooleanField(default=True)
    email_swap_request = models.BooleanField(default=True)
    email_leave_status = models.BooleanField(default=True)
    
    # In-app preferences
    app_shift_assigned = models.BooleanField(default=True)
    app_swap_request = models.BooleanField(default=True)
    app_leave_status = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'notification_preferences'

class Notification(models.Model):
    """In-app notifications."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
```

#### Phase 2: Email Templates (Day 2)

**Create Template Directory**:
```bash
mkdir -p team_planner/notifications/templates/emails
```

**1. Shift Assignment Email**
**File**: `team_planner/notifications/templates/emails/shift_assigned.html`

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #1976d2; color: white; padding: 20px; }
        .content { padding: 20px; background: #f5f5f5; }
        .button { background: #1976d2; color: white; padding: 10px 20px; 
                  text-decoration: none; border-radius: 5px; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>New Shift Assignment</h2>
        </div>
        <div class="content">
            <p>Hello {{ user.first_name }},</p>
            <p>You have been assigned to a new shift:</p>
            <ul>
                <li><strong>Date:</strong> {{ shift.date|date:"F j, Y" }}</li>
                <li><strong>Time:</strong> {{ shift.start_time|time:"g:i A" }} - {{ shift.end_time|time:"g:i A" }}</li>
                <li><strong>Type:</strong> {{ shift.shift_type.name }}</li>
                <li><strong>Location:</strong> {{ shift.location|default:"Not specified" }}</li>
            </ul>
            <p><a href="{{ schedule_url }}" class="button">View Schedule</a></p>
        </div>
    </div>
</body>
</html>
```

#### Phase 3: Notification Service (Day 3)

**File**: `team_planner/notifications/services.py`

```python
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Notification, NotificationPreference, NotificationType

class NotificationService:
    """Service for sending notifications."""
    
    def notify_shift_assigned(self, shift):
        """Send notification when shift is assigned."""
        user = shift.employee.user
        prefs = self._get_preferences(user)
        
        # Send email
        if prefs.email_shift_assigned:
            self._send_shift_email(user, shift, 'shift_assigned')
        
        # Create in-app notification
        if prefs.app_shift_assigned:
            Notification.objects.create(
                user=user,
                type=NotificationType.SHIFT_ASSIGNED,
                title='New Shift Assignment',
                message=f'You have been assigned to {shift.shift_type.name} on {shift.date}',
                link=f'/schedule?date={shift.date}'
            )
    
    def notify_swap_request(self, swap_request):
        """Notify user of swap request."""
        target_user = swap_request.target_employee.user
        prefs = self._get_preferences(target_user)
        
        if prefs.email_swap_request:
            context = {
                'user': target_user,
                'swap_request': swap_request,
                'requester': swap_request.requesting_employee.user,
            }
            html_message = render_to_string('emails/swap_request.html', context)
            send_mail(
                subject='New Shift Swap Request',
                message='',
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_user.email],
            )
        
        if prefs.app_swap_request:
            Notification.objects.create(
                user=target_user,
                type=NotificationType.SWAP_REQUEST,
                title='Swap Request Received',
                message=f'{swap_request.requesting_employee.user.get_full_name()} wants to swap shifts',
                link=f'/swaps/{swap_request.id}'
            )
    
    def _get_preferences(self, user):
        """Get or create notification preferences."""
        prefs, created = NotificationPreference.objects.get_or_create(user=user)
        return prefs
```

#### Phase 4: Integration with Views (Day 4)

**Integrate in Shift Views**:
```python
from team_planner.notifications.services import NotificationService

class ShiftViewSet(viewsets.ModelViewSet):
    
    def perform_create(self, serializer):
        shift = serializer.save()
        # Send notification
        notification_service = NotificationService()
        notification_service.notify_shift_assigned(shift)
```

**Estimated Time**: 3-4 days  
**Priority**: HIGH (User Experience)

---

### Priority 3: Frontend Notification UI ⭐⭐

#### 1. Notification Bell Component
**File**: `frontend/src/components/NotificationBell.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Badge, IconButton, Menu, MenuItem, Typography } from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import apiClient from '../services/apiClient';

interface Notification {
  id: number;
  title: string;
  message: string;
  link: string;
  is_read: boolean;
  created_at: string;
}

export const NotificationBell: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    loadNotifications();
    // Poll every 30 seconds
    const interval = setInterval(loadNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadNotifications = async () => {
    try {
      const response = await apiClient.get('/api/notifications/');
      const data = response.results || response;
      setNotifications(data);
      setUnreadCount(data.filter((n: Notification) => !n.is_read).length);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  };

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleNotificationClick = async (notification: Notification) => {
    // Mark as read
    await apiClient.patch(`/api/notifications/${notification.id}/`, { is_read: true });
    // Navigate to link
    if (notification.link) {
      window.location.href = notification.link;
    }
    handleClose();
    loadNotifications();
  };

  return (
    <>
      <IconButton color="inherit" onClick={handleClick}>
        <Badge badgeContent={unreadCount} color="error">
          <NotificationsIcon />
        </Badge>
      </IconButton>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        PaperProps={{
          style: { maxHeight: 400, width: 350 }
        }}
      >
        {notifications.length === 0 ? (
          <MenuItem disabled>
            <Typography variant="body2">No notifications</Typography>
          </MenuItem>
        ) : (
          notifications.map((notification) => (
            <MenuItem
              key={notification.id}
              onClick={() => handleNotificationClick(notification)}
              sx={{
                backgroundColor: notification.is_read ? 'transparent' : '#e3f2fd',
                borderBottom: '1px solid #eee',
                flexDirection: 'column',
                alignItems: 'flex-start',
                py: 1.5
              }}
            >
              <Typography variant="subtitle2" fontWeight="bold">
                {notification.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {notification.message}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {new Date(notification.created_at).toLocaleDateString()}
              </Typography>
            </MenuItem>
          ))
        )}
      </Menu>
    </>
  );
};
```

#### 2. Add to Navigation
**File**: `frontend/src/components/SideNavigation.tsx`

```typescript
import { NotificationBell } from './NotificationBell';

// In the AppBar section:
<NotificationBell />
```

**Estimated Time**: 1 day  
**Priority**: MEDIUM

---

## 🔧 MEDIUM PRIORITY (Week 7-8: Reports & Exports)

### Priority 4: Essential Reports ⭐⭐

#### Reports to Implement:

1. **Schedule Export** (PDF/Excel)
   - Weekly/monthly schedule
   - Employee-specific schedule
   - Team schedule

2. **Fairness Report**
   - Distribution of shifts by employee
   - Weekend/holiday balance
   - Hours worked comparison

3. **Leave Report**
   - Leave balance by employee
   - Upcoming leave calendar
   - Leave history

4. **Swap History Report**
   - Swap requests by user
   - Approval/rejection rates
   - Swap patterns

**Implementation**:
- Use `django-reportlab` for PDF generation
- Use `openpyxl` for Excel generation
- Add download buttons to existing pages
- Cache reports for performance

**Estimated Time**: 5-6 days  
**Priority**: MEDIUM

---

## 📊 SUMMARY: Next 4 Weeks

| Week | Focus | Priority | Status |
|------|-------|----------|--------|
| Week 5 | Backend Permission Enforcement | HIGH | 🔄 Next |
| Week 5-6 | Email Notification System | HIGH | 📋 Planned |
| Week 6 | Frontend Notification UI | MEDIUM | 📋 Planned |
| Week 7-8 | Reports & Exports | MEDIUM | 📋 Planned |

---

## 🎯 Success Criteria

### Week 5 Complete When:
- ✅ All API endpoints enforce permissions
- ✅ 403 errors returned for unauthorized access
- ✅ Email notification system working
- ✅ At least 3 notification types implemented

### Week 6 Complete When:
- ✅ Notification bell in navigation
- ✅ In-app notifications display
- ✅ Mark as read functionality works
- ✅ Email templates for all key events

### Week 7-8 Complete When:
- ✅ Schedule export to PDF/Excel
- ✅ Fairness report generated
- ✅ Leave report available
- ✅ All reports downloadable

---

## 🚀 Quick Start: Begin Week 5

### Step 1: Create Permission Decorator
```bash
touch team_planner/rbac/decorators.py
```

### Step 2: Test Permission Enforcement
```bash
# As a Read-Only user, try to create a shift (should get 403)
curl -X POST http://localhost:8000/api/shifts/ \
  -H "Authorization: Token <readonly_token>" \
  -H "Content-Type: application/json" \
  -d '{"date":"2025-10-15","shift_type":1}'
```

### Step 3: Create Notifications App
```bash
cd team_planner
python manage.py startapp notifications
```

### Step 4: Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 📝 Notes

- **Testing**: Each feature should have unit tests before merging
- **Documentation**: Update API docs with permission requirements
- **Performance**: Add database indexes for notification queries
- **Security**: All notification links should be validated

---

**Ready to proceed with Week 5: Backend Permission Enforcement?**
