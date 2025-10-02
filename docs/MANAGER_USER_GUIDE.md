# Team Planner - Manager User Guide

**Version:** 1.0  
**Last Updated:** October 2, 2025  
**Audience:** Team Leads, Managers, Supervisors

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Team Schedule Management](#team-schedule-management)
4. [Approval Workflows](#approval-workflows)
5. [Managing Shift Swaps](#managing-shift-swaps)
6. [Managing Leave Requests](#managing-leave-requests)
7. [Conflict Resolution](#conflict-resolution)
8. [Team Management](#team-management)
9. [Reports and Analytics](#reports-and-analytics)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Getting Help](#getting-help)

---

## 1. Getting Started

### 1.1 Manager Role and Permissions

As a manager, you have additional permissions beyond regular employees:

**Your Capabilities:**
- View and manage team schedules
- Approve/reject shift swap requests
- Approve/reject leave requests
- Create and assign shifts
- Manage team members
- Generate reports
- Resolve scheduling conflicts
- Configure approval rules

**What You Cannot Do:**
- Modify system settings (Admin only)
- Create new users (Admin only)
- Change user roles (Admin only)
- Access other teams' data (unless multi-team manager)

### 1.2 Accessing Manager Features

**Navigation Menu:**

Additional menu items visible to managers:
- **Team Schedule** - Create and manage shifts
- **Pending Approvals** - Review swap requests
- **Leave Approvals** - Review leave requests
- **Approval Rules** - Configure approval workflows
- **Team Members** - Manage your team
- **Reports** - Generate analytics
- **Conflict Resolution** - Manage scheduling conflicts

### 1.3 First Steps as a New Manager

1. **Review Your Team**
   - Go to **Team Members**
   - Verify team composition
   - Check employee skills and certifications
   - Note availability preferences

2. **Review Current Schedule**
   - Go to **Team Schedule**
   - Check upcoming shifts
   - Identify coverage gaps
   - Review pending requests

3. **Check Pending Items**
   - Go to **Pending Approvals**
   - Review outstanding swap requests
   - Go to **Leave Approvals**
   - Review pending leave requests

4. **Configure Preferences**
   - Set notification preferences
   - Configure approval rules (if authorized)
   - Set default view options

---

## 2. Dashboard Overview

### 2.1 Manager Dashboard

Access your dashboard from the home page or by clicking **Dashboard**.

**Dashboard Widgets:**

**Team Status Summary:**
- Total team members
- Currently on duty
- On leave today
- Available employees

**Pending Actions:**
- Swap requests awaiting approval: [count]
- Leave requests awaiting approval: [count]
- Unassigned shifts: [count]
- Conflicts requiring attention: [count]

**Upcoming Events:**
- Next 7 days schedule summary
- Upcoming leave periods
- Training sessions
- Special events

**Quick Stats:**
- Shifts this week
- Coverage percentage
- Average hours per employee
- Overtime hours

**Recent Activity:**
- Latest swap approvals
- Latest leave approvals
- Recent schedule changes
- System notifications

### 2.2 Customizing Your Dashboard

1. Click **Customize Dashboard**
2. Drag and drop widgets to reorder
3. Show/hide widgets as needed
4. Set refresh interval
5. Save preferences

### 2.3 Dashboard Notifications

**Color Coding:**
- 🟢 Green: All good, no action needed
- 🟡 Yellow: Attention needed soon
- 🔴 Red: Urgent action required

**Badge Indicators:**
- Red badge number = urgent items
- Blue badge number = informational items

---

## 3. Team Schedule Management

### 3.1 Viewing Team Schedule

**Calendar View:**

1. Go to **Team Schedule** → **Calendar**
2. View options:
   - Month view - Full month overview
   - Week view - Detailed weekly schedule
   - Day view - Single day breakdown
   - List view - Tabular format

**Filter Options:**
- Filter by employee
- Filter by shift type
- Filter by team (if multi-team manager)
- Show/hide unassigned shifts
- Show/hide leave periods

**Color Coding:**
- Blue: Regular shifts
- Green: Approved swaps
- Yellow: Pending changes
- Red: Conflicts or gaps
- Gray: Leave periods
- Purple: Training shifts

### 3.2 Creating Shifts

**Method 1: Calendar Click**

1. Go to **Team Schedule**
2. Click on date/time where you want to create shift
3. Fill in shift details:
   - Shift type (incident, standby, training, etc.)
   - Start time
   - End time
   - Location (if applicable)
   - Employee (or leave unassigned)
   - Notes/description
4. Click **Create Shift**

**Method 2: From List View**

1. Go to **Team Schedule** → **List View**
2. Click **Create Shift** button
3. Fill in all details
4. Click **Save**

**Shift Details:**

- **Shift Type**: Select from configured types
- **Employee**: Assign to specific employee or leave unassigned
- **Date & Time**: Start and end date/time
- **Location**: Work location if applicable
- **Team**: Your team (auto-selected)
- **Required Skills**: Optional skill requirements
- **Notes**: Special instructions

**Validation:**

System automatically checks for:
- Employee availability
- Skill matching
- Overtime limits
- Rest period requirements
- Leave conflicts
- Double-booking prevention

Warnings appear if issues detected.

### 3.3 Bulk Shift Creation

**Using Templates:**

1. Go to **Team Schedule** → **Bulk Operations**
2. Select **Create from Template**
3. Choose shift template
4. Select date range
5. Choose assignment strategy:
   - **Round Robin**: Rotate through team members
   - **Skills Match**: Assign based on required skills
   - **Availability**: Prefer available employees
   - **Fair Distribution**: Balance hours evenly
6. Preview assignments
7. Click **Create Shifts**

**Using Recurring Patterns:**

1. Go to **Team Schedule** → **Recurring Patterns**
2. Click **Create Pattern**
3. Define pattern:
   - Recurrence type (daily, weekly, bi-weekly, monthly)
   - Start date
   - End date (or ongoing)
   - Shift details
   - Employee assignment
4. Preview upcoming shifts
5. Click **Generate Shifts**

### 3.4 Modifying Shifts

**Edit Single Shift:**

1. Click on shift in calendar
2. Click **Edit** button
3. Modify details:
   - Time change
   - Employee reassignment
   - Shift type change
   - Notes update
4. Click **Save Changes**

**Bulk Modifications:**

1. Go to **Bulk Operations** → **Modify Times**
2. Select shifts to modify:
   - By date range
   - By employee
   - By shift type
3. Choose modification:
   - Set new times
   - Offset times (shift by X hours)
4. Preview changes
5. Click **Apply**

### 3.5 Deleting Shifts

**Delete Single Shift:**

1. Click on shift
2. Click **Delete** button
3. Confirm deletion
4. Shift removed, employee notified

**Bulk Delete:**

1. Go to **Bulk Operations** → **Delete**
2. Select shifts by criteria
3. Review list of shifts to delete
4. Optional: Check **Force delete** (override conflicts)
5. Click **Delete Shifts**
6. Confirm action

**Warning:** Deleted shifts cannot be recovered. Employees are automatically notified.

### 3.6 Assigning Employees to Shifts

**Manual Assignment:**

1. Find unassigned shift
2. Click shift
3. Click **Assign Employee**
4. Select employee from dropdown
5. System checks:
   - Availability
   - Skills match
   - Conflicts
   - Overtime limits
6. Review warnings (if any)
7. Click **Assign**

**Bulk Assignment:**

1. Go to **Bulk Operations** → **Assign Employees**
2. Select unassigned shifts
3. Choose assignment method:
   - Auto-assign by availability
   - Auto-assign by skills
   - Auto-assign round-robin
   - Manual selection
4. Preview assignments
5. Review conflict warnings
6. Click **Assign All**

### 3.7 Handling Unassigned Shifts

**View Unassigned Shifts:**

1. Go to **Team Schedule**
2. Enable **Show Unassigned** filter
3. Unassigned shifts highlighted in red

**Quick Assign:**

1. Click unassigned shift
2. Click **Quick Assign**
3. System suggests best matches based on:
   - Availability
   - Skills
   - Hours balance
   - Preferences
4. Select suggested employee
5. Click **Assign**

---

## 4. Approval Workflows

### 4.1 Understanding Approval Levels

Your organization may use single or multi-level approvals:

**Single-Level Approval:**
- You approve/reject directly
- Decision is final
- Immediate effect

**Multi-Level Approval:**
- Level 1: Team Lead (you)
- Level 2: Department Manager
- Level 3: Operations Manager
- Each level must approve sequentially

**Your Approval Chain:**

View in **Approval Rules** to see:
- What approvals require your action
- What approvals go to higher levels
- Auto-approval criteria

### 4.2 Configuring Approval Rules

**If You Have Rule Management Permission:**

1. Go to **Approval Rules**
2. Click **Create Rule**
3. Configure rule:

**Basic Information:**
- Rule name (descriptive)
- Priority (higher = evaluated first)
- Active status
- Shift types (apply to which types)

**Approval Levels:**
- Number of levels required (1-5)
- Who approves at each level

**Auto-Approval Criteria:**
- Enable auto-approval toggle
- Set conditions:
  * Same shift type swap
  * Minimum advance notice (hours)
  * Minimum seniority (months)
  * Skills match required
- Set monthly swap limit per employee

4. Click **Create Rule**

**Rule Priority:**

Rules evaluated from highest to lowest priority:
- Priority 200: Emergency swaps
- Priority 100: Standard swaps
- Priority 50: Training swaps
- Lower priorities for special cases

**Example Rule:**

```
Name: "Standard Same-Type Swap"
Priority: 100
Levels: 1
Auto-Approve: Yes
Conditions:
  - Same shift type: Yes
  - Advance hours: 48+
  - Seniority: 3+ months
  - Skills match: Yes
Monthly limit: 4 swaps
```

This rule auto-approves swaps that meet all conditions.

### 4.3 Delegation of Approval Authority

**Temporary Delegation:**

When you're on leave or unavailable:

1. Go to **Approval Rules** → **Delegations**
2. Click **Create Delegation**
3. Fill in details:
   - Delegate to (select manager)
   - Start date
   - End date
   - Reason (optional)
4. Click **Create**

**Incoming Delegations:**

When someone delegates to you:
- You'll receive notification
- Delegated approvals marked with badge
- You have full approval authority during delegation
- Original manager can still see history

---

## 5. Managing Shift Swaps

### 5.1 Viewing Pending Swap Requests

1. Go to **Pending Approvals**
2. See all swap requests awaiting your approval

**Table Columns:**
- **Requesting Employee**: Who wants to swap
- **Target Employee**: Who they want to swap with
- **Original Shift**: Date and time
- **Swap Shift**: What they'll take (if applicable)
- **Current Level**: Approval progress (e.g., "Level 1 of 2")
- **Submitted**: When request was created
- **Actions**: View, Approve, Reject

**Summary Cards:**
- Total pending: [count]
- Delegated to you: [count]
- Multi-level: [count]
- Urgent (< 48 hours): [count]

### 5.2 Reviewing a Swap Request

**View Full Details:**

1. Click **View** icon on request
2. Details dialog shows:

**Swap Information:**
- Both employees
- Both shifts (full details)
- Reason for swap
- Submission date
- Auto-approval eligibility

**Approval Chain:**
- Visual stepper showing levels
- Current progress highlighted
- Previous approvers (if multi-level)

**Employee Information:**
- Swap history (past swaps this month)
- Current hours
- Attendance record
- Skills verification

**Conflict Checks:**
- Coverage maintained: ✅ or ⚠️
- Skills match: ✅ or ⚠️
- No overtime issues: ✅ or ⚠️
- Rest periods respected: ✅ or ⚠️

**Audit Trail:**
- Request created
- Employee acceptance
- Previous approvals
- Comments from stakeholders

### 5.3 Approving a Swap Request

**To Approve:**

1. Review all details
2. Verify coverage maintained
3. Check for policy compliance
4. Click **Approve** button
5. Add optional comments
6. Click **Confirm Approval**

**What Happens:**
- If final level: Swap immediately processed, schedules updated
- If not final: Moves to next approval level
- Both employees notified
- Calendar updates automatically
- Audit trail recorded

**Approval Tips:**

✅ **Approve When:**
- Coverage maintained
- Skills appropriate
- Fair distribution
- Valid business reason
- Policy compliant

⚠️ **Consider Carefully:**
- Short notice swaps
- Frequent swapper
- Coverage borderline
- Skills marginal
- Pattern of issues

### 5.4 Rejecting a Swap Request

**To Reject:**

1. Click **Reject** button
2. Enter reason (required)
3. Suggestions:
   - "Insufficient coverage"
   - "Skills mismatch"
   - "Too short notice"
   - "Monthly limit exceeded"
   - "Fairness concern"
   - Custom reason
4. Click **Confirm Rejection**

**What Happens:**
- Request immediately denied
- Both employees notified with reason
- Original shifts remain unchanged
- Audit trail updated

**Rejection Best Practices:**

- Always provide clear, specific reason
- Be constructive in feedback
- Suggest alternatives if possible
- Be consistent in application
- Document patterns of issues

### 5.5 Delegating a Specific Approval

**For One-Time Delegation:**

1. Open swap request
2. Click **Delegate** button
3. Select manager to delegate to
4. Add note explaining delegation
5. Click **Delegate**

**When to Delegate:**
- Conflict of interest (family member)
- Specialized knowledge needed
- You're unsure of department policy
- Cross-team coordination needed

---

## 6. Managing Leave Requests

### 6.1 Viewing Leave Requests

1. Go to **Leave Approvals**
2. See all leave requests for your team

**Filter Options:**
- Pending only
- All statuses
- By leave type
- By date range
- By employee

**Request Details:**
- Employee name
- Leave type
- Start and end dates
- Duration (days)
- Reason
- Conflicts (if any)
- Submitted date
- Status

### 6.2 Reviewing Leave Requests

**Click on Request to View:**

**Employee Information:**
- Leave balance for this type
- Leave used this year
- Other pending leave
- Attendance record
- Seniority

**Leave Details:**
- Type and duration
- Dates requested
- Reason provided
- Supporting documents (if any)
- Alternative dates suggested

**Impact Analysis:**
- Team coverage during period
- Other team members on leave
- Scheduled shifts affected
- Special events/busy periods
- Minimum staffing met: ✅ or ⚠️

**Conflict Warnings:**

🔴 **Critical Conflicts:**
- Minimum staffing not met
- Key skills unavailable
- Already assigned shifts
- Blackout period violation

🟡 **Minor Conflicts:**
- Multiple team members on leave
- Busy period
- Short staffing

### 6.3 Approving Leave Requests

**To Approve:**

1. Review employee leave balance
2. Check team coverage
3. Verify no critical conflicts
4. Click **Approve** button
5. Add optional comments
6. Click **Confirm Approval**

**What Happens:**
- Leave balance reduced
- Calendar updated with leave period
- Conflicting shifts removed or reassigned
- Employee notified
- Leave shows on team calendar

**Approval Considerations:**

✅ **Approve When:**
- Sufficient leave balance
- Coverage maintained
- Reasonable notice given
- Valid business reason
- Fair distribution

⚠️ **Carefully Review:**
- Last-minute requests
- Busy period leave
- Multiple overlapping leave
- Extended leave periods
- Pattern of Monday/Friday leave

### 6.4 Rejecting Leave Requests

**To Reject:**

1. Click **Reject** button
2. Select rejection reason:
   - Insufficient coverage
   - Insufficient leave balance
   - Blackout period
   - Too short notice
   - Business needs
   - Other (explain)
3. Add detailed explanation
4. Suggest alternative dates (optional)
5. Click **Confirm Rejection**

**Rejection Best Practices:**

- Be prompt - don't delay
- Be specific about reason
- Suggest alternatives when possible
- Be consistent and fair
- Document business justification
- Follow organization policy

### 6.5 Conditional Approvals

**Approve with Conditions:**

Some systems allow conditional approval:

1. Click **Approve with Conditions**
2. Specify conditions:
   - Different dates
   - Shorter duration
   - Partial approval
   - Pending coverage
3. Employee can accept or modify

**When to Use:**
- Can approve some but not all dates
- Coverage possible with adjustments
- Compromise beneficial
- Flexibility available

### 6.6 Managing Conflicting Leave

**When Multiple Employees Request Same Dates:**

**Conflict Resolution Strategies:**

1. **First Come, First Served**
   - Approve in order received
   - Document decision basis

2. **Seniority Based**
   - Senior employees get preference
   - Fair and consistent

3. **Rotating Priority**
   - Track who got preference last time
   - Alternate priority

4. **Business Need**
   - Evaluate impact of each approval
   - Choose least impact option

5. **Negotiated Solution**
   - Contact employees
   - Propose alternatives
   - Seek compromise

**Document Your Decision:**
- Record rationale in notes
- Explain to affected employees
- Be transparent and consistent

---

## 7. Conflict Resolution

### 7.1 Accessing Conflict Dashboard

1. Go to **Conflict Resolution**
2. See all scheduling conflicts for your team

**Conflict Types:**

🔴 **Critical:**
- Double-booked employees
- Shift without qualified employee
- Minimum staffing violation
- Rest period violation

🟡 **Warnings:**
- Overtime approaching limit
- Skills coverage thin
- Multiple employees on leave
- Unassigned shifts

### 7.2 Reviewing Conflicts

**Click on Conflict to View:**

**Conflict Details:**
- Type and severity
- Affected employees
- Affected shifts
- Time period
- Impact assessment

**Suggested Resolutions:**

System provides AI-powered suggestions:

1. **Reassign shift** - Move to different employee
2. **Adjust timing** - Change shift times
3. **Split shift** - Divide among multiple employees
4. **Cancel shift** - Remove if not critical
5. **Overtime approval** - Allow exceeding limits
6. **External coverage** - Use agency/contractor

### 7.3 Resolving Conflicts

**Manual Resolution:**

1. Review conflict details
2. Choose resolution approach
3. Take action:
   - Reassign employees
   - Modify shift times
   - Cancel conflicting items
   - Approve exceptions
4. Document decision in notes
5. Click **Mark as Resolved**

**Using AI Recommendations:**

1. Review suggested resolutions
2. Click **Apply Recommendation**
3. Preview changes
4. Confirm application
5. System implements changes
6. Affected parties notified

**Resolution Priority:**

1. Safety-critical conflicts (immediate)
2. Staffing minimums (same day)
3. Coverage gaps (within 48 hours)
4. Optimization issues (when convenient)

---

## 8. Team Management

### 8.1 Viewing Team Members

1. Go to **Team Members**
2. See all employees in your team

**Member Information:**
- Name and employee ID
- Role and seniority
- Contact information
- Skills and certifications
- Availability preferences
- Current status (active, on leave, etc.)
- Hours this period

### 8.2 Managing Team Composition

**If You Have Permission:**

**Add Member to Team:**

1. Click **Add Member**
2. Search for employee
3. Select employee
4. Set role in team
5. Click **Add**

**Remove Member from Team:**

1. Find member
2. Click **Remove**
3. Specify reason
4. Choose effective date
5. Confirm removal

**Note:** Usually coordinated with HR and Admin.

### 8.3 Viewing Employee Schedules

**Individual Schedule:**

1. Click on employee name
2. View their schedule:
   - Upcoming shifts
   - Past shifts
   - Leave periods
   - Swap history
   - Hours summary

**Compare Schedules:**

1. Select multiple employees
2. Click **Compare Schedules**
3. See side-by-side view
4. Identify patterns
5. Balance workload

### 8.4 Managing Employee Skills

**View Skills:**

1. Click employee name
2. Go to **Skills** tab
3. See certified skills and levels

**Request Skill Verification:**

1. Click **Request Verification**
2. Select skill to verify
3. Add notes
4. Submit to admin

**Skill-Based Scheduling:**

When creating shifts:
- Filter employees by required skills
- System highlights skill matches
- Warnings for skill gaps

---

## 9. Reports and Analytics

### 9.1 Available Reports

**Go to Reports Section:**

**Schedule Reports:**
- Team schedule summary
- Coverage analysis
- Shift distribution
- Unassigned shifts report

**Time Reports:**
- Hours worked by employee
- Overtime report
- Undertime report
- Hours by shift type

**Leave Reports:**
- Leave balance summary
- Leave taken report
- Leave trends
- Leave conflicts report

**Swap Reports:**
- Swap request summary
- Approval turnaround times
- Most active swappers
- Swap denial reasons

**Performance Reports:**
- Attendance summary
- Late/missed shifts
- Reliability metrics
- Team performance scorecard

### 9.2 Generating Reports

**Standard Reports:**

1. Select report type
2. Set parameters:
   - Date range
   - Team(s)
   - Employee(s)
   - Filters
3. Click **Generate Report**
4. View on screen
5. Export if needed (PDF, Excel, CSV)

**Custom Reports:**

1. Click **Custom Report**
2. Select data fields
3. Set grouping and sorting
4. Apply filters
5. Preview report
6. Save template (optional)
7. Generate and export

### 9.3 Scheduled Reports

**Set Up Automatic Reports:**

1. Create/select report
2. Click **Schedule Report**
3. Configure:
   - Frequency (daily, weekly, monthly)
   - Day/time
   - Email recipients
   - Format (PDF, Excel)
4. Click **Save Schedule**

**Example:** Weekly hours report every Monday at 8am.

### 9.4 Report Analysis

**Key Metrics to Monitor:**

**Coverage:**
- Target: 95%+ shifts assigned
- Minimum staffing always met
- Skills coverage adequate

**Efficiency:**
- Average hours per employee
- Overtime percentage (<10% ideal)
- Swap approval time (<24 hours)

**Fairness:**
- Hours distribution (standard deviation)
- Weekend shift distribution
- Undesirable shift rotation

**Compliance:**
- Rest period violations (0 target)
- Maximum shift length compliance
- Union rules compliance (if applicable)

---

## 10. Best Practices

### 10.1 Schedule Creation

**Weekly Workflow:**

1. **Monday:** Review upcoming 2-week schedule
2. **Tuesday:** Create new shifts for week 3
3. **Wednesday:** Assign employees to unassigned shifts
4. **Thursday:** Review and approve pending requests
5. **Friday:** Address any conflicts, finalize week 1

**Best Practices:**

- Publish schedule 2 weeks in advance
- Maintain consistency in shift patterns
- Balance desirable/undesirable shifts fairly
- Consider employee preferences when possible
- Document changes and rationale
- Communicate proactively

### 10.2 Approval Management

**Timely Approvals:**

- Review requests daily
- Respond within 24 hours
- Urgent requests (< 48 hours) within 4 hours
- Don't let requests sit

**Consistent Decisions:**

- Apply same criteria to all employees
- Document decision rationale
- Follow organizational policies
- Be fair and transparent

**Communication:**

- Provide feedback on denials
- Suggest alternatives
- Be approachable
- Keep employees informed

### 10.3 Conflict Prevention

**Proactive Strategies:**

1. **Advance Planning**
   - Create schedules early
   - Anticipate busy periods
   - Plan for known absences

2. **Clear Communication**
   - Set expectations clearly
   - Publish blackout dates
   - Explain scheduling rules

3. **Fair Distribution**
   - Track hours balance
   - Rotate undesirable shifts
   - Consider preferences equally

4. **Regular Review**
   - Weekly schedule review
   - Monthly pattern analysis
   - Quarterly fairness check

### 10.4 Team Morale

**Scheduling for Satisfaction:**

- Honor preferences when possible
- Allow shift swaps liberally (when safe)
- Approve leave fairly
- Recognize flexibility
- Explain constraints honestly
- Be consistent

**Red Flags:**

- Frequent swap requests (burnout?)
- Declining leave requests
- Last-minute calls-offs
- Pattern of tardiness

Address issues early through conversation.

---

## 11. Troubleshooting

### Common Issues

**Issue: Cannot Approve Swap Request**

**Solutions:**
1. Check if you have approval permission for this shift type
2. Verify request is at your approval level
3. Ensure not delegated to someone else
4. Check if auto-approval already processed it
5. Contact admin if permissions issue

**Issue: Schedule Changes Not Saving**

**Solutions:**
1. Check internet connection
2. Verify you have edit permissions
3. Check for validation errors (red highlights)
4. Try refreshing page
5. Check if shift is locked (past date)
6. Contact support if persists

**Issue: Employee Not Appearing in Assignment List**

**Solutions:**
1. Check if employee is in your team
2. Verify employee is active (not terminated)
3. Check if employee has required skills
4. Verify no conflicting assignments
5. Check if employee on leave during shift
6. Verify employee availability settings

**Issue: Conflict Warnings Not Resolving**

**Solutions:**
1. Verify all conflicting items addressed
2. Check if new conflicts created
3. Refresh conflict dashboard
4. Click "Recheck Conflicts"
5. Contact support if false positive

---

## 12. Getting Help

### Support Resources

**Internal Support:**

**For Scheduling Questions:**
- Contact: Your manager or HR
- Email: scheduling@yourcompany.com
- Phone: (555) 123-4567 ext. 2

**For Technical Issues:**
- Contact: IT Help Desk
- Email: support@yourcompany.com
- Phone: (555) 123-4567
- Hours: 24/7

**For Policy Questions:**
- Contact: HR Department
- Email: hr@yourcompany.com
- Phone: (555) 123-4567 ext. 3

### Manager Training

**Available Training:**

- New Manager Onboarding (4 hours)
- Advanced Scheduling Techniques (2 hours)
- Conflict Resolution Workshop (2 hours)
- Reporting and Analytics (1 hour)
- Quarterly Manager Roundtables

**Contact:** training@yourcompany.com

### Documentation

- Employee User Guide
- Admin User Guide
- Quick Reference Cards
- Video Tutorials
- FAQ Database

**Access:** Help menu → Documentation

---

## Quick Reference

### Daily Tasks Checklist

- [ ] Review pending swap approvals
- [ ] Review pending leave requests
- [ ] Check for scheduling conflicts
- [ ] Review upcoming shifts (next 48 hours)
- [ ] Respond to employee questions
- [ ] Address urgent notifications

### Weekly Tasks Checklist

- [ ] Create schedule for week N+2
- [ ] Review unassigned shifts
- [ ] Check team coverage
- [ ] Generate hours report
- [ ] Review conflict trends
- [ ] Address staffing gaps
- [ ] Follow up on pending items

### Monthly Tasks Checklist

- [ ] Review monthly reports
- [ ] Analyze swap/leave patterns
- [ ] Check fairness metrics
- [ ] Update availability preferences
- [ ] Review and update approval rules
- [ ] Conduct team schedule review
- [ ] Plan for next month's needs

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl/Cmd + A | Approve selected request |
| Ctrl/Cmd + R | Reject selected request |
| Ctrl/Cmd + N | Create new shift |
| Ctrl/Cmd + F | Open filters |
| Ctrl/Cmd + K | Quick search |
| Esc | Close dialog |

---

## Glossary

**Manager-Specific Terms:**

- **Approval Chain**: Sequence of approvers for a request
- **Auto-Approval**: Automatic approval based on rules
- **Blackout Period**: Dates when leave not allowed
- **Coverage**: Adequate staffing for operations
- **Delegation**: Temporary transfer of approval authority
- **Fair Distribution**: Equitable assignment of shifts
- **Multi-Level Approval**: Requires multiple sequential approvals
- **Override**: Manager decision despite system warnings
- **Priority**: Order in which rules are evaluated
- **Round Robin**: Rotating assignment method

---

**Document End**

**Version:** 1.0  
**Last Updated:** October 2, 2025  
**Next Review:** January 2, 2026

For the latest version, visit Help → Manager Documentation.
