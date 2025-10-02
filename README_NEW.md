# Team Planner

**Advanced Shift Scheduling & Team Management System**

A comprehensive platform for managing team schedules, shift swaps, leave requests, and resource planning with enterprise-grade security and intelligent scheduling algorithms.

[![Built with Django](https://img.shields.io/badge/Django-5.1.11-green.svg)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18.3.1-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6.2-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Current Status

**Phase 1 Complete:** ✅ MFA, ✅ User Registration, ✅ RBAC, ✅ Unified Management Console  
**Phase 2 Current:** 🔄 Backend Permission Enforcement & Notification System

📋 **See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for detailed roadmap and next steps.**

---

## ✨ Key Features

### 🔐 Security & Access Control
- **Multi-Factor Authentication (MFA)** with TOTP and backup codes
- **Role-Based Access Control (RBAC)** with 5 roles and 22 granular permissions
- **User Registration** with admin approval workflow
- **Token-based Authentication** for API access

### 👥 User & Team Management
- **Unified Management Console** for users, teams, roles, and departments
- **Department Management** with hierarchy support
- **Team Member Management** with role assignments
- **User Activation/Deactivation** workflows

### 📅 Scheduling Features
- **Shift Scheduling** with multiple shift types
- **Shift Swap Requests** with approval workflows
- **Leave Management** with multiple leave types
- **Schedule Orchestration** with intelligent algorithms
- **Fairness Calculations** for balanced shift distribution

### 🎨 Modern UI/UX
- **Responsive Design** works on desktop and mobile
- **Material-UI Components** for consistent design
- **Permission-Based Navigation** showing only authorized features
- **Real-time Updates** with hot module replacement in development

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Development Setup (5 minutes)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd team_planner

# 2. Start the application
docker-compose up

# 3. Access the application
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Admin:    http://localhost:8000/admin
```

### Default Credentials
- **Username:** `admin`
- **Password:** `admin123`

### First Steps
1. Login with admin credentials
2. Navigate to **Management** to create users, teams, and departments
3. Assign roles to users
4. Start creating shifts and schedules!

---

## 🏗️ Technology Stack

### Backend
- **Django 5.1.11** - Web framework
- **Django REST Framework 3.15.2** - API framework
- **SQLite** (dev) / **PostgreSQL** (production) - Database
- **TOTP (pyotp)** - Multi-factor authentication
- **Python 3.11+** - Programming language

### Frontend
- **React 18.3.1** - UI framework
- **TypeScript 5.6.2** - Type safety
- **Vite 6.3.6** - Build tool & dev server
- **Material-UI 6.3.1** - Component library
- **Redux Toolkit** - State management
- **React Router 7.1.1** - Routing

### DevOps
- **Docker & Docker Compose** - Containerization
- **Nginx** (production) - Reverse proxy
- **GitHub Actions** (planned) - CI/CD

---

## 📂 Project Structure

```
team_planner/
├── config/                 # Django settings & configuration
├── team_planner/          # Django apps
│   ├── users/            # User management & MFA
│   ├── rbac/             # Role-based access control
│   ├── teams/            # Team & department management
│   ├── shifts/           # Shift scheduling
│   ├── leaves/           # Leave management
│   └── orchestrators/    # Scheduling algorithms
├── frontend/              # React TypeScript application
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API services
│   │   ├── hooks/       # Custom React hooks
│   │   └── types/       # TypeScript type definitions
│   └── public/          # Static assets
├── docs/                  # Documentation
│   ├── guides/          # Setup & deployment guides
│   └── archive/         # Historical progress reports
└── docker-compose.yml     # Docker configuration
```

---

## 🧪 Testing

### Run Backend Tests
```bash
# All tests
docker-compose exec django python manage.py test

# Specific app
docker-compose exec django python manage.py test team_planner.users

# With coverage
docker-compose exec django pytest --cov=team_planner
```

### Run Frontend Tests
```bash
cd frontend
npm test
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) | Current status, priorities, and next steps |
| [NEXT_STEPS_ROADMAP.md](NEXT_STEPS_ROADMAP.md) | Detailed implementation guide for upcoming features |
| [Getting Started](docs/guides/GETTING_STARTED.md) | Step-by-step setup instructions |
| [Deployment Guide](docs/guides/DEPLOYMENT.md) | Production deployment instructions |
| [Docker Guide](docs/guides/DOCKER_DEPLOYMENT.md) | Container setup and management |
| [Phase 1 Plan](docs/guides/PHASE_1_IMPLEMENTATION_PLAN.md) | Original 8-10 week implementation plan |

---

## 👥 User Roles & Permissions

### 5 User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| **Super Admin** | Full system access | All permissions |
| **Manager** | Department/team oversight | Approve requests, view reports |
| **Shift Planner** | Schedule management | Create/edit shifts, run orchestrator |
| **Employee** | Regular user | View schedule, request swaps/leave |
| **Read-Only** | View-only access | View schedules and reports only |

### 22 Granular Permissions

**Schedule Permissions:** View, create, edit, delete shifts  
**Swap Permissions:** Request, approve, reject swaps  
**Leave Permissions:** Request, approve, reject leave  
**Management Permissions:** Manage users, teams, departments, roles  
**Orchestrator Permissions:** Run scheduling algorithms, view results  

---

## 🔄 Development Workflow

### Making Changes

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Backend Development**
   - Add models, serializers, views
   - Run migrations: `python manage.py makemigrations && python manage.py migrate`
   - Write tests
   - Apply RBAC permissions

3. **Frontend Development**
   - Create components/pages
   - Add TypeScript types
   - Implement permission gates
   - Test with different user roles

4. **Testing**
   - Backend: `python manage.py test`
   - Frontend: `npm test`
   - Manual testing in browser

5. **Documentation**
   - Update API docs
   - Add inline comments
   - Update roadmap if needed

---

## 🤝 Contributing

We welcome contributions! Please:

1. Check [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for current priorities
2. Create a feature branch from `main`
3. Write tests for your changes
4. Ensure all tests pass
5. Update documentation
6. Submit a pull request

---

## 📊 Project Metrics

- **Backend Tests:** 150+ tests
- **Test Coverage:** ~75%
- **API Endpoints:** 45+ endpoints
- **Database Migrations:** 85+ migrations
- **Lines of Code:** ~20,000 (backend) + ~15,000 (frontend)

---

## 🗺️ Roadmap Highlights

### ✅ Completed (Weeks 1-4)
- Multi-Factor Authentication
- User Registration & Approval
- Role-Based Access Control
- Unified Management Console
- Department Management

### 🔄 In Progress (Week 5-6)
- Backend Permission Enforcement
- Email Notification System
- In-App Notifications

### 📋 Planned (Week 7+)
- Reports & Exports (PDF/Excel)
- Advanced Scheduling Features
- Performance Optimization
- Production Deployment

**See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for complete roadmap.**

---

## 🐛 Troubleshooting

### Docker Issues
```bash
# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Database Issues
```bash
# Reset database
docker-compose exec django python manage.py flush
docker-compose exec django python manage.py migrate
docker-compose exec django python manage.py createsuperuser
```

### Frontend Issues
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

---

## 📞 Support

- **Documentation:** Check `docs/guides/` directory
- **Issues:** Submit via GitHub Issues
- **Historical Context:** See `docs/archive/` for progress reports

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Django](https://www.djangoproject.com/) and [React](https://reactjs.org/)
- UI components from [Material-UI](https://mui.com/)
- Initial project structure from [Cookiecutter Django](https://github.com/cookiecutter/cookiecutter-django/)

---

**Ready to start developing?** 

👉 See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for next steps and priorities!
