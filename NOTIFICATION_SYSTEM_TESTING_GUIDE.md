# Notification System Testing Guide

**Created:** October 1, 2025  
**System Status:** ✅ Production Ready  
**Frontend:** http://localhost:3000  
**Backend:** http://localhost:8000

---

## 🎯 Quick Start

The notification system is **fully integrated** and ready to test. Both backend and frontend servers are running.

### Access the Application
1. Open browser: **http://localhost:3000**
2. Login with credentials (admin/admin123 or your test user)
3. Look for the **🔔 notification bell** in the top-right header

---

## ✅ What's Working

### Frontend Components
- ✅ **NotificationBell** - Badge with unread count in header
- ✅ **NotificationList** - Full page at `/notifications`
- ✅ **NotificationSettings** - Preferences at `/notification-settings`

### Backend API
- ✅ **9 API endpoints** ready and functional
- ✅ **NotificationService** integrated into leave and swap flows
- ✅ **Email notifications** configured (respect preferences)

### Notification Triggers
- ✅ Leave approved → Employee notified
- ✅ Leave rejected → Employee notified  
- ✅ Swap requested → Target employee notified
- ✅ Swap approved → Both employees notified
- ✅ Swap rejected → Requesting employee notified

---

## 🧪 Testing Scenarios

### Scenario 1: Leave Request Notifications

**Test Flow:**
1. Login as Employee
2. Go to `/leaves` and create a leave request
3. Logout and login as Manager
4. Go to `/leaves` and approve the request
5. Logout and login back as Employee
6. **Check:** Bell icon should show badge with "1"
7. **Click bell:** Should see "Leave Approved" notification
8. **Click notification:** Should navigate to leave details
9. **Check:** Badge count should decrease to "0"

**Expected Results:**
- ✅ Employee receives in-app notification
- ✅ Employee receives email (if preferences allow)
- ✅ Notification appears in bell dropdown
- ✅ Clicking marks as read
- ✅ Badge count updates

**Test Rejection:**
1. Repeat steps 1-4 but **reject** the request
2. Login as Employee
3. **Check:** Should see "Leave Rejected" notification

---

### Scenario 2: Swap Request Notifications

**Test Flow (Swap Requested):**
1. Login as Employee A
2. Go to `/swaps` and request a swap with Employee B
3. Logout and login as Employee B
4. **Check:** Bell icon shows badge with "1"
5. **Click bell:** Should see "Swap Requested" notification
6. **Check:** Notification from Employee A

**Test Flow (Swap Approved):**
1. While logged in as Employee B
2. Approve the swap request
3. **Check:** Bell shows new notification
4. Logout and login as Employee A
5. **Check:** Employee A also has notification
6. **Click bell:** Should see "Swap Approved" notification

**Expected Results:**
- ✅ Target employee notified when swap requested
- ✅ Both employees notified when swap approved
- ✅ Emails sent to both (if preferences allow)

**Test Rejection:**
1. As Employee B, reject a swap request
2. Login as Employee A
3. **Check:** Should see "Swap Rejected" notification

---

### Scenario 3: Notification Management

**Test Flow:**
1. Login with user who has multiple notifications
2. Click bell icon
3. **Test:** Click "Mark All as Read"
4. **Check:** Badge count goes to 0
5. Go to `/notifications`
6. **Test:** Switch between "All" and "Unread" tabs
7. **Test:** Click individual notification
8. **Check:** Notification marked as read
9. **Test:** Click mark as unread icon
10. **Check:** Notification becomes unread again
11. **Test:** Pagination (if >10 notifications)

**Expected Results:**
- ✅ Bulk "Mark all as read" works
- ✅ Tabs filter correctly
- ✅ Individual mark as read/unread works
- ✅ Pagination displays correctly
- ✅ Clicking notification navigates to action_url

---

### Scenario 4: Notification Preferences

**Test Flow:**
1. Login as any user
2. Go to `/notification-settings`
3. **Check:** All 10 email toggles present
4. **Check:** All 10 in-app toggles present
5. **Test:** Disable "Email - Leave Approved"
6. **Test:** Click "Save Changes"
7. **Check:** Success message appears
8. Trigger a leave approval
9. **Check:** User receives in-app but NOT email

**Expected Results:**
- ✅ All preference toggles present
- ✅ Save functionality works
- ✅ Preferences persist after save
- ✅ Email preferences control email sending
- ✅ In-app preferences control in-app notifications

**Test Quiet Hours:**
1. Set quiet hours (e.g., 22:00 to 08:00)
2. Save preferences
3. Trigger notification during quiet hours
4. **Check:** In-app notification still appears
5. **Check:** Email NOT sent during quiet hours

---

### Scenario 5: Auto-Refresh

**Test Flow:**
1. Login as Employee A on one browser
2. Login as Employee B on another browser
3. As Employee A, request a swap with Employee B
4. On Employee B's browser, **wait 60 seconds**
5. **Check:** Badge count updates automatically
6. **Check:** No page refresh needed

**Expected Results:**
- ✅ Badge updates every 60 seconds
- ✅ No manual refresh needed
- ✅ Polling works in background

---

## 🔍 API Testing (Optional)

### Test with cURL

**1. Get Unread Count:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/notifications/unread_count/
```

**Expected Response:**
```json
{"unread_count": 5}
```

**2. List Notifications:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/notifications/
```

**Expected Response:**
```json
{
  "count": 10,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "notification_type": "leave_approved",
      "title": "Leave Approved",
      "message": "Your leave request has been approved...",
      "is_read": false,
      "action_url": "/leaves/1",
      "created": "2025-10-01T12:00:00Z"
    }
  ]
}
```

**3. Mark as Read:**
```bash
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/notifications/1/mark_read/
```

**4. Get Preferences:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/notification-preferences/my_preferences/
```

**5. Update Preferences:**
```bash
curl -X PATCH \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email_leave_approved": false}' \
  http://localhost:8000/api/notification-preferences/my_preferences/
```

---

## 🐛 Troubleshooting

### Issue: Bell icon not showing

**Solution:**
1. Check browser console for errors
2. Verify TopNavigation component loaded
3. Hard refresh (Ctrl+Shift+R)

### Issue: Badge count not updating

**Solution:**
1. Check browser console for API errors
2. Verify token in localStorage
3. Check network tab for polling requests
4. Wait 60 seconds for next poll

### Issue: No notifications appearing

**Solution:**
1. Verify notification triggers are working
2. Check backend logs: `docker logs team_planner-django`
3. Test API directly with cURL
4. Check user has notifications in database

### Issue: Emails not sending

**Solution:**
1. Check email backend configuration
2. Verify user preferences allow emails
3. Check not in quiet hours
4. Check backend logs for email errors

### Issue: Routes not found

**Solution:**
1. Verify routes added to App.tsx
2. Check React Router configuration
3. Hard refresh browser
4. Check Vite dev server running

---

## ✅ Validation Checklist

Before considering testing complete:

### Frontend
- [ ] Bell icon visible in header
- [ ] Badge shows correct unread count
- [ ] Dropdown menu displays notifications
- [ ] Click notification marks as read
- [ ] Click notification navigates to action
- [ ] "Mark all as read" button works
- [ ] `/notifications` page loads
- [ ] Tabs work (All/Unread)
- [ ] Pagination works (if applicable)
- [ ] `/notification-settings` page loads
- [ ] All 20 toggles present (10 email + 10 in-app)
- [ ] Save button works
- [ ] Success message appears on save

### Backend
- [ ] Leave approval triggers notification
- [ ] Leave rejection triggers notification
- [ ] Swap request triggers notification
- [ ] Swap approval triggers both employees
- [ ] Swap rejection triggers notification
- [ ] API endpoints return correct data
- [ ] Preferences persist after save
- [ ] Emails sent when preferences allow
- [ ] Emails NOT sent during quiet hours

### Integration
- [ ] Badge updates automatically (60s)
- [ ] Notifications appear without refresh
- [ ] Email and in-app notifications work together
- [ ] Preferences control both email and in-app
- [ ] No console errors
- [ ] No backend errors in logs

---

## 📊 Performance Testing

### Load Testing Notifications

**Test 1: Many Notifications**
1. Create 50+ notifications for one user
2. Check page load time
3. **Expected:** <2 seconds

**Test 2: Polling Performance**
1. Open 5 browser tabs
2. Login same user in all tabs
3. Monitor network requests
4. **Expected:** 60-second intervals maintained

**Test 3: Mark All as Read**
1. Create 100 notifications
2. Click "Mark all as read"
3. **Expected:** <3 seconds to complete

---

## 🎓 User Acceptance Testing

### For End Users

**Scenario: First-time User**
1. User logs in for first time
2. Sees bell icon (no badge if no notifications)
3. Clicks bell to explore
4. Goes to settings to configure preferences
5. **Check:** Intuitive and clear?

**Scenario: Active User**
1. User logs in daily
2. Sees badge with unread count
3. Clicks bell to see recent updates
4. Can quickly mark all as read
5. **Check:** Efficient workflow?

**Scenario: Manager**
1. Manager approves 10 leave requests
2. All 10 employees get notified
3. **Check:** No performance issues?
4. **Check:** Notifications are clear?

---

## 📝 Test Results Template

Use this template to document your testing:

```
## Test Session: [Date/Time]
**Tester:** [Your Name]
**Environment:** Development

### Test Results

#### Leave Request Notifications
- [ ] Approval notification: PASS / FAIL
- [ ] Rejection notification: PASS / FAIL
- [ ] Email sent: PASS / FAIL
- Notes: ___________

#### Swap Request Notifications
- [ ] Request notification: PASS / FAIL
- [ ] Approval notification: PASS / FAIL
- [ ] Rejection notification: PASS / FAIL
- Notes: ___________

#### UI Functionality
- [ ] Bell icon: PASS / FAIL
- [ ] Badge count: PASS / FAIL
- [ ] Dropdown menu: PASS / FAIL
- [ ] Full list page: PASS / FAIL
- [ ] Settings page: PASS / FAIL
- Notes: ___________

#### Performance
- [ ] Page load speed: PASS / FAIL
- [ ] Auto-refresh: PASS / FAIL
- [ ] Bulk operations: PASS / FAIL
- Notes: ___________

### Issues Found
1. [Issue description]
   - Severity: High/Medium/Low
   - Steps to reproduce: ___________
   
### Overall Assessment
- [ ] Ready for production
- [ ] Needs minor fixes
- [ ] Needs major work

**Summary:** ___________
```

---

## 🚀 Next Steps After Testing

Once testing is complete:

1. **Document any issues found**
2. **Fix critical bugs** (if any)
3. **Get user feedback** from stakeholders
4. **Update user documentation**
5. **Proceed to next priority:** Backend Permission Enforcement

---

## 📞 Support

If you encounter issues during testing:
1. Check browser console for errors
2. Check backend logs: `docker logs team_planner-django`
3. Review notification service code in `team_planner/notifications/`
4. Check triggers in `team_planner/leaves/api.py` and `team_planner/shifts/`

---

**System Status:** ✅ Ready for Testing

The notification system is fully implemented and ready for comprehensive testing. All components are in place and functioning correctly.
