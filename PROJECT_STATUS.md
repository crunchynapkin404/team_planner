# Team Planner - Project Setup Complete

## Project Overview

**Team Planner** is a sophisticated shift scheduling system built with Cookiecutter Django. It implements an advanced orchestrator for fair shift distribution across multiple shift types with comprehensive leave management and swap functionality.

## Current Status: Phase 2 Complete ✅

Following the 16-week roadmap, **Phase 1: Foundation & Models** and **Phase 2: Orchestrator Engine** have been successfully implemented.

### Implemented Features

#### � **Phase 2: Orchestrator Engine (COMPLETE)**
- **ShiftOrchestrator** - Fair distribution algorithm with 52-week planning capability
- **FairnessCalculator** - Assignment tracking and deviation minimization
- **ConstraintChecker** - Availability toggles, leave conflicts, and overlap prevention
- **Manual Trigger Interface** - Form-based orchestration with preview mode
- **Orchestration Dashboard** - History tracking and fairness metrics
- **Preview Mode** - Review assignments before applying changes
- **Integration Layer** - Seamless integration with Phase 1 models

#### �🏗️ **Phase 1: Core Models Architecture (COMPLETE)**
- **EmployeeProfile** - Extended user profiles with shift availability toggles
- **EmployeeSkill** - Skills system for shift assignment eligibility
- **Team & Department** - Organizational structure with membership system
- **LeaveType, LeaveRequest, Holiday** - Comprehensive leave management
- **Shift, ShiftTemplate** - Core shift scheduling framework
- **SwapRequest** - Shift exchange system between employees
- **FairnessScore** - Fair distribution tracking system
- **TimeEntry, OvertimeEntry** - Time tracking and overtime management

#### 🔧 **Shift Availability System**
- `available_for_incidents` - Boolean flag for incident shift eligibility (Mon-Fri, 8:00-17:00)
- `available_for_waakdienst` - Boolean flag for on-call shift eligibility (evenings, nights, weekends)
- Skills-based assignment requirements through `EmployeeSkill` model

#### 📊 **Admin Interface**
- Comprehensive admin panels for all models
- Custom fieldsets and filtering for efficient management
- Inline editing for related models (e.g., LeaveBalance in EmployeeProfile)
- Search functionality across key fields

#### 🗄️ **Database & Migrations**
- All models created and migrated successfully
- SQLite development database configured
- Proper indexes and constraints implemented
- Database relationships established

### Key Architecture Decisions

1. **Cookiecutter Django Structure**: Maintained standard cookiecutter-django project layout
2. **Model Organization**: Separated concerns into logical apps (employees, teams, leaves, shifts)
3. **Skill System**: Simple boolean toggles for shift availability rather than complex skill matrices
4. **Fairness Tracking**: Separate scoring for incidents vs waakdienst for independent fairness calculations
5. **Admin-First Approach**: Comprehensive admin interface for immediate usability

## Project Structure

```
team_planner/
├── config/                    # Django settings
├── team_planner/             # Main Django package
│   ├── employees/           # Employee management app
│   │   ├── models.py       # EmployeeProfile, EmployeeSkill, LeaveBalance
│   │   ├── admin.py        # Admin configuration
│   │   └── migrations/     # Database migrations
│   ├── teams/              # Team/Department management
│   ├── leaves/             # Leave management system
│   ├── shifts/             # Shift scheduling framework
│   ├── orchestrators/      # Phase 2: Automatic scheduling orchestrator
│   │   ├── algorithms.py   # ShiftOrchestrator, FairnessCalculator, ConstraintChecker
│   │   ├── models.py       # OrchestrationRun, OrchestrationResult
│   │   ├── views.py        # Dashboard, creation, preview interfaces
│   │   ├── forms.py        # OrchestrationForm, DateRangeForm
│   │   └── urls.py         # Orchestrator URL routing
│   ├── users/              # User authentication
│   └── static/             # Static files
├── requirements/           # Python dependencies
├── docker-compose.*.yml   # Docker configurations
├── manage.py              # Django management
└── justfile              # Build automation
```

## Next Steps: Phase 3 - Swap & Leave System

With Phase 2 complete, the next phase involves building the shift swapping and integrated leave management system:

### Planned Features
1. **Shift Swapping System** - Engineer-to-engineer shift exchanges with approval workflow
2. **Leave Integration** - Block leave requests until shifts are reassigned
3. **Notification System** - Real-time notifications for swap requests and approvals
4. **Swap Request Management** - Dashboard for pending/approved/rejected swaps
5. **Automated Conflict Resolution** - Handle conflicts between swaps and orchestrator assignments

### Technical Requirements
- SwapRequest model enhancement for workflow states
- Approval chain implementation (manager/admin approval)
- Integration with orchestrator for automatic reassignment
- Email/notification system for swap workflow
- Leave request blocking mechanism

## Running the Project

### Local Development (Current Setup)
```bash
cd /home/bart/VsCode/TeamPlanner/team_planner

# Set environment variables
export DATABASE_URL="sqlite:///db.sqlite3"
export USE_DOCKER="no"
export DJANGO_SETTINGS_MODULE="config.settings.local"

# Run migrations (if needed)
.venv/bin/python manage.py migrate

# Start development server
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

### Admin Access
- URL: http://127.0.0.1:8000/admin/
- Username: admin
- Password: (set during superuser creation)

### Docker Setup (Production)
```bash
# Build containers
docker compose -f docker-compose.local.yml build

# Start services
docker compose -f docker-compose.local.yml up -d

# Run migrations
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
```

## Development Environment

- **Python**: 3.13.5 (Virtual environment: `.venv/`)
- **Django**: 5.1.11
- **Database**: SQLite (development), PostgreSQL (production)
- **Key Packages**: DRF, django-allauth, celery, django-crispy-forms

## Cookiecutter Principles Followed

1. **✅ Separation of Concerns**: Apps organized by domain (employees, teams, leaves)
2. **✅ Settings Organization**: Environment-specific settings (local, production, test)
3. **✅ Docker Integration**: Full containerization support
4. **✅ Security Best Practices**: Proper environment variable handling
5. **✅ Testing Structure**: Test files in place for each app
6. **✅ Documentation**: Comprehensive README and model documentation
7. **✅ Internationalization**: Translation strings used throughout
8. **✅ Admin Interface**: Django admin fully configured
9. **✅ Static Files**: Proper static file organization
10. **✅ Database Migrations**: Proper migration management

## Business Logic Implemented

### Shift Types (Roadmap Compliant)
- **Incidents**: Business hours (8:00-17:00), Monday-Friday, 1 engineer per week
- **Waakdienst**: After hours + weekends, 1 engineer per week
- **Changes & Projects**: Default assignment for non-incident engineers

### Availability System
- Engineers opt-in to incident/waakdienst shifts via boolean flags
- Skills system ready for future requirement expansion
- Leave integration blocks assignments during approved leave

### Fair Distribution Framework
- Separate tracking for incident days vs waakdienst days
- Period-based fairness calculations (configurable time ranges)
- Historical assignment data for orchestrator algorithms

## Success Metrics (Phase 1 & 2)

### Phase 1 ✅
- ✅ All database models created and migrated
- ✅ Basic API endpoints functional (admin interface)
- ✅ Admin interface for data management
- ✅ Cookiecutter project structure maintained
- ✅ Environment configuration working
- ✅ Local development server running

### Phase 2 ✅
- ✅ Fair distribution orchestrator with 52-week planning
- ✅ Manual trigger interface with preview mode
- ✅ Constraint handling (availability, leave, conflicts)
- ✅ Fairness calculation and tracking system
- ✅ Integration with Phase 1 models
- ✅ Comprehensive testing and validation

**Phase 1 & 2 are now complete and ready for Phase 3 development.**
