# Team Planner - Project Roadmap

## Questions for Clarification

Before documenting the complete roadmap, I need clarification on several key aspects:

### 1. Shift Types & Orchestrator Details

**Incidents (Automatic Scheduling):**
- **Type**: IT/Technical incidents
- **Schedule**: Monday-Friday, 8:00-17:00 (business hours only)
- **Duration**: Full week assignments (same engineer Mo-Fri)
- **Coverage**: 1 engineer per shift
- **Skill Requirement**: Only engineers with "incident" skill
- **Planning Horizon**: 52 weeks (full year planning)
- **Availability**: All engineers fully available except holidays and approved leave
- **Leave Handling**: Engineers must swap shifts with colleagues if they need leave during their assigned week
- **Fairness**: Equal distribution of incident weeks across all qualified engineers over the entire year

**Waakdienst (Automatic Scheduling):**
- **Type**: On-call/Standby duty (complementary to Incidents)
- **Schedule**: 
  - **Weekdays**: 17:00-08:00 next day (when Incidents shift is off)
  - **Weekends**: Full 24 hours (Saturday & Sunday)
- **Duration**: Full week assignments (same engineer Wednesday 17:00 to next Wednesday 08:00)
- **Coverage**: 1 engineer per shift
- **Relationship to Incidents**: Covers all hours when Incident shift is NOT active
- **Planning**: Same rules as Incidents (52-week planning, equal distribution, swap system)

**Orchestrator Considerations:**
- Generate both Incident and Waakdienst schedules seperately
- Ensure no engineer has both Incident and Waakdienst in the same week
- Fair distribution across both shift types combined

**Changes & Projects (Manual Scheduling):**
- **Type**: Regular daily work assignments (default when not on Incidents)
- **Schedule**: Business hours (08:00-17:00) Monday-Friday
- **Assignment Logic**: Automatic fallback - any engineer NOT assigned to Incidents will work on Changes & Projects
- **Management**: Team Leads/Planners manually assign specific projects/changes to available engineers
- **Duration**: Flexible based on project/change requirements

### 2. Time Tracking & Fairness

**Time Tracking Requirements:**
- Track actual days worked for each shift type
- Separate calculations for Incidents vs Waakdienst
- Daily granularity for precise fairness tracking

**Fairness Calculation:**
- **Incidents**: Count total days assigned to Incident shifts (5 days per week)
- **Waakdienst**: Count total days assigned to Waakdienst shifts (7 days per week)
- **Independent Tracking**: Incident fairness and Waakdienst fairness calculated separately
- **Distribution Period**: Per year fairness (equal distribution within the selected planning period)
- **Manual Planning**: Planner can manually trigger orchestrator and select custom planning periods

### 3. User Roles & Permissions

**User (Base Level):**
- View their own schedule
- Request shift swaps with other users
- Approve incoming swap requests directed to them
- Request leave
- View team calendar (read-only)

**Team Lead:**
- All User permissions
- Approve shift swaps for their team members
- Approve leave requests for their team
- Assign Projects & Changes to available team members
- Run orchestrator for planning periods
- View team schedules and reports
- Manage team composition and member assignments

**Admin:**
- All permissions (full system access)
- User management (create, edit, deactivate users)
- System configuration
- Cross-team operations
- Advanced reporting and analytics
- Audit logs access

**Role System:**
- Users can have multiple roles (e.g., User + Team Lead + Admin)
- Planner role may be merged with Team Lead (to be determined during development)

### 4. Calendar & Frontend Requirements

**Calendar Views:**
- **Month View**: Traditional monthly calendar grid
- **Week View**: Detailed weekly schedule view
- **Year View**: Overview of entire year for long-term planning
- **Timeline View**: Gantt-style timeline for detailed scheduling

**Calendar Functionality:**
- **Drag & Drop**: Move shifts between dates and engineers
- **Smart Swap Requests**: When dragging to another engineer, automatically trigger swap request dialog
- **Visual Clarity**: Easy identification of who has which shift assignment
- **Color Coding**: Different colors for each shift type (Incidents, Waakdienst, Changes, Projects)
- **Conflict Prevention**: System prevents overlapping shift assignments
- **Real-time Updates**: Live updates when changes are made

**Display Requirements:**
- Clear engineer names on shift blocks
- Shift type identification
- Time ranges visible
- Status indicators (confirmed, pending, swap requested)

### 5. Technical Preferences

**Frontend Technology Stack:**
- **Framework**: React with Vite (fast build, modern tooling, cookiecutter compatible)
- **Calendar Library**: FullCalendar.js (most feature-rich, excellent drag-drop, multiple views)
- **UI Framework**: Material-UI (MUI) - comprehensive components, professional look
- **State Management**: Redux Toolkit (predictable state, great dev tools, scales well)
- **HTTP Client**: Axios with React Query (caching, background updates, error handling)

**Integration with Django:**
- **API**: Django REST Framework with proper CORS setup
- **Authentication**: Token-based auth integrated with Django's user system
- **WebSockets**: Django Channels for real-time calendar updates
- **Build Integration**: Serve React build from Django static files

**Key Libraries for Requirements:**
- **Drag & Drop**: @dnd-kit (modern, accessible, works well with FullCalendar)
- **Form Handling**: React Hook Form + Yup validation
- **Notifications**: React Hot Toast for user feedback
- **Icons**: Material Icons (consistent with MUI)

### 6. Business Logic & Organizational Structure

**Skills System:**
- Simple toggle on user profile: "Available for Incidents" (Yes/No)
- Simple toggle on user profile: "Available for Waakdienst" (Yes/No)
- Orchestrator only includes users with relevant toggles enabled

**Team Structure:**
- One team per engineer (single team membership)
- Multiple engineers per team
- Team-based permissions and reporting

**Leave Request Workflow:**
1. Engineer requests leave during assigned shift period
2. System shows popup: "You have shifts assigned during this period that need reassignment"
3. System automatically suggests available engineers for swapping
4. Engineer creates swap requests to suggested engineers
5. Target engineers receive swap requests and can accept/decline
6. Once swap is accepted, leave request becomes available for approval
7. Team Lead approves the leave request
8. **Leave is blocked until swap is fully arranged and approved**

**Shift Reassignment Process:**
- System finds engineers with matching availability toggles
- Suggests engineers who are available during the requested period
- Engineers must explicitly accept swap requests
- No automatic reassignment without explicit consent

**Company Holidays:**
- Ignored for initial implementation (can be added later)

---

## 📋 IMPLEMENTATION PHASES

### PHASE 1: Foundation & Models (Week 1-2)
**Goal**: Complete backend infrastructure and database schema

#### Tasks:
1. **Create Shifts App**
   - Shift models (Shift, ShiftTemplate, ShiftAssignment)
   - Availability toggles on User profile (incidents/waakdienst)
   - Swap request models (SwapRequest, SwapResponse)

2. **Extend Existing Models**
   - Update Team model for single membership
   - Add shift availability fields to user profiles
   - Leave request integration with shift checking

3. **Database Migrations**
   - Create all new models
   - Update existing relationships
   - Add proper indexes for performance

4. **Core APIs**
   - CRUD endpoints for shifts and swaps
   - User availability management
   - Leave request with shift validation

#### Deliverables:
- ✅ All database models created and migrated
- ✅ Basic API endpoints functional
- ✅ Admin interface for data management

### PHASE 2: Orchestrator Engine (Week 3-4)
**Goal**: Build the automatic scheduling orchestrator

#### Tasks:
1. **Orchestrator Algorithm**
   - Fair distribution algorithm for incidents (5-day weeks)
   - Fair distribution algorithm for waakdienst (7-day weeks)
   - Constraint handling (availability toggles, existing leave)
   - Conflict resolution logic

2. **Orchestrator Interface**
   - Manual trigger with date range selection
   - Preview mode before confirming
   - Fairness calculation display
   - Historical assignment tracking

3. **Business Logic**
   - Prevent overlapping assignments
   - Respect user availability toggles
   - Handle partial periods and edge cases

#### Deliverables:
- ✅ Working orchestrator with fair distribution
- ✅ Manual planning interface
- ✅ Fairness calculation system

### PHASE 3: Swap & Leave System (Week 5-6)
**Goal**: Implement shift swapping and leave management

#### Tasks:
1. **Swap Request System**
   - Create swap requests between engineers
   - Automatic suggestion of available engineers
   - Approval/rejection workflow
   - Notification system

2. **Leave Integration**
   - Detect shifts during leave periods
   - Block leave until swaps arranged
   - Popup warnings for conflicting shifts
   - Integration with swap approval process

3. **Validation & Rules**
   - Prevent invalid swaps
   - Maintain fairness after swaps
   - Audit trail for all changes

#### Deliverables:
- ✅ Complete swap request system
- ✅ Integrated leave management
- ✅ Validation and business rules

### PHASE 4: Frontend Foundation (Week 7-8) ✅ COMPLETE
**Goal**: Build React frontend with basic functionality

#### Tasks:
1. **Project Setup**
   - ✅ React + Vite setup
   - ✅ Material-UI integration
   - ✅ Redux Toolkit configuration
   - ✅ API integration with Django

2. **Core Components**
   - ✅ Authentication system
   - ✅ User dashboard
   - ✅ Basic navigation
   - ✅ Role-based UI rendering

3. **API Integration**
   - ✅ HTTP client setup
   - ✅ Error handling
   - ✅ Loading states
   - ✅ Token management

#### Deliverables:
- ✅ Working React application
- ✅ Authentication flow
- ✅ Basic UI framework

### PHASE 5: Calendar Interface (Week 9-10)
**Goal**: Build the advanced calendar system

#### Tasks:
1. **Calendar Implementation**
   - FullCalendar.js integration
   - Multiple views (month, week, year, timeline)
   - Color coding for shift types
   - Engineer identification on shifts

2. **Drag & Drop Functionality**
   - Drag shifts between dates
   - Drag to different engineers triggers swap
   - Visual feedback and validation
   - Conflict prevention

3. **Interactive Features**
   - Click to view shift details
   - Real-time updates via WebSockets
   - Filtering by engineer/team/shift type
   - Responsive design

#### Deliverables:
- ✅ Fully functional calendar interface
- ✅ Drag & drop swap requests
- ✅ Real-time updates

### PHASE 6: Orchestrator UI (Week 11-12)
**Goal**: Build the planning interface

#### Tasks:
1. **Planning Dashboard**
   - Date range selection
   - Orchestrator trigger interface
   - Preview mode with approval
   - Progress indicators

2. **Fairness Dashboard**
   - Visual fairness metrics
   - Historical assignment charts
   - Engineer workload comparison
   - Detailed fairness breakdown

3. **Admin Features**
   - Bulk operations
   - Manual adjustments
   - Override capabilities
   - Audit logs

#### Deliverables:
- ✅ Complete orchestrator interface
- ✅ Fairness visualization
- ✅ Administrative controls

### PHASE 7: User Management & Permissions (Week 13-14)
**Goal**: Complete role-based access control

#### Tasks:
1. **Permission System**
   - Role-based UI components
   - API endpoint protection
   - Multi-role support
   - Permission inheritance

2. **User Interface**
   - Profile management
   - Availability toggle controls
   - Team assignment interface
   - Role management (Admin only)

3. **Team Management**
   - Team creation and editing
   - Member assignment
   - Team-based reporting
   - Team Lead permissions

#### Deliverables:
- ✅ Complete permission system
- ✅ User and team management
- ✅ Role-based access control

### PHASE 8: Testing & Polish (Week 15-16)
**Goal**: Comprehensive testing and final improvements

#### Tasks:
1. **Testing**
   - Unit tests for critical algorithms
   - Integration tests for API endpoints
   - Frontend component testing
   - End-to-end user workflows

2. **Performance Optimization**
   - Database query optimization
   - Frontend bundle optimization
   - Caching strategies
   - Load testing

3. **Documentation**
   - User manual
   - API documentation
   - Deployment guide
   - Troubleshooting guide

#### Deliverables:
- ✅ Comprehensive test suite
- ✅ Performance optimizations
- ✅ Complete documentation

---

## 🎯 SUCCESS CRITERIA

### Core Functionality:
- ✅ Orchestrator generates fair 52-week schedules
- ✅ Engineers can swap shifts with approval workflow
- ✅ Leave requests blocked until shifts reassigned
- ✅ Calendar shows all shifts with clear visual hierarchy
- ✅ Role-based permissions working correctly

### Performance Goals:
- ✅ Orchestrator completes 52-week planning in under 30 seconds
- ✅ Calendar loads and renders smoothly with 1000+ shifts
- ✅ Real-time updates propagate within 2 seconds
- ✅ System supports 100+ concurrent users

### User Experience:
- ✅ Intuitive drag-and-drop calendar interface
- ✅ Clear fairness visualization
- ✅ Responsive design for various screen sizes
- ✅ Comprehensive error messages and validation

---

## 🚀 DEPLOYMENT STRATEGY

### Development Environment:
- Docker Compose for local development
- Hot reloading for both Django and React
- Shared PostgreSQL and Redis containers

### Production Environment:
- Django + React served from same domain
- PostgreSQL with connection pooling
- Redis for caching and Celery
- Nginx for static file serving
- Docker containers with health checks

---

## 📊 ESTIMATED TIMELINE

**Total Duration**: 16 weeks (4 months)
**Team Size**: 1-2 developers
**Key Milestones**:
- Week 4: Working orchestrator
- Week 6: Complete swap system
- Week 10: Functional calendar interface
- Week 14: Feature complete
- Week 16: Production ready

---

## Next Steps

Once this roadmap is approved, we can begin with Phase 1: Foundation & Models.
