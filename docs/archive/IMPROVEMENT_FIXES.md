# Team Planner Improvement Fixes

## 🚨 Critical Fixes (Do These First)

### 1. Fix TypeScript Errors (37 errors found)

#### A. Fix Test Import Issues
```bash
# Fix useOrchestrator test file
cd frontend/src/hooks/__tests__
# Replace all instances of 'mockedXXXAsync' with 'mockXXXAsync'
```

#### B. Fix Type Interface Issues
```typescript
// In src/hooks/useOrchestrator.ts - Export the return type properly
export interface UseOrchestratorReturn {
  // ... existing interface
}

export const useOrchestrator = (): UseOrchestratorReturn => {
  // ... existing implementation
}
```

#### C. Fix Calendar Type Compatibility
```typescript
// In src/types/calendar.ts - Align shift types
export type ShiftType = 
  | 'incidents' 
  | 'waakdienst' 
  | 'incidents_standby' 
  | 'incident' 
  | 'project' 
  | 'change';
```

#### D. Remove Unused Imports
```bash
cd frontend
npx eslint src/ --fix
```

### 2. Security & Dependency Issues

#### A. Fix npm audit issues
```bash
cd frontend
npm audit fix
```

#### B. Update deprecated packages
```bash
npm update
```

### 3. Fix API Proxy Configuration

#### A. Update frontend config for local development
```typescript
// vite.config.ts - Add local development override
export default defineConfig({
  // ... existing config
  server: {
    proxy: {
      '/api': {
        target: process.env.NODE_ENV === 'development' 
          ? 'http://localhost:8000'  // Local development
          : 'http://django:8000',    // Docker
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
```

## 🔧 Performance Optimizations

### 1. Backend Query Optimization
```python
# Add select_related and prefetch_related to reduce database queries
# In models.py files, add proper indexing

class ShiftQuerySet(models.QuerySet):
    def with_relations(self):
        return self.select_related(
            'assigned_employee',
            'template',
            'template__shift_type'
        ).prefetch_related(
            'swap_requests',
            'time_entries'
        )
```

### 2. Frontend Bundle Optimization
```typescript
// Add code splitting for better performance
const Dashboard = lazy(() => import('./pages/Dashboard'));
const CalendarPage = lazy(() => import('./pages/CalendarPage'));
```

### 3. Database Indexing
```python
# Add to models
class Meta:
    indexes = [
        models.Index(fields=['start_datetime', 'end_datetime']),
        models.Index(fields=['assigned_employee', 'status']),
    ]
```

## 🧪 Testing Improvements

### 1. Increase Frontend Test Coverage
```bash
cd frontend
npm run test:coverage
# Target: >80% coverage
```

### 2. Add E2E Tests
```bash
npm install --save-dev playwright
# Create tests/e2e/ directory with critical user flows
```

### 3. Backend Integration Tests
```python
# Add more comprehensive integration tests
# Test complete workflows: Schedule creation → Assignment → Swap → Approval
```

## 🏗️ Architecture Improvements

### 1. Clean Architecture Consistency
- Move all business logic to domain services
- Implement proper repository patterns
- Add CQRS pattern for complex operations

### 2. API Versioning
```python
# Implement proper API versioning
urlpatterns = [
    path('api/v1/', include('api.v1.urls')),
    path('api/v2/', include('api.v2.urls')),
]
```

### 3. Event Sourcing for Audit Trail
```python
# Implement event sourcing for critical operations
class ShiftAssignmentEvent(Event):
    shift_id: int
    employee_id: int
    timestamp: datetime
    event_type: str
```

## 📖 Documentation Improvements

### 1. Consolidate Deployment Docs
- Merge DOCKER_DEPLOYMENT.md and PORTAINER_DEPLOYMENT.md
- Create single DEPLOYMENT.md with clear sections

### 2. API Documentation
```bash
# Generate comprehensive API docs
python manage.py spectacular --color --file schema.yml
```

### 3. Frontend Component Documentation
```bash
cd frontend
npm install --save-dev storybook
# Create stories for all major components
```

## 🚀 DevOps & Deployment

### 1. CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Backend Tests
        run: |
          docker-compose -f docker-compose.test.yml up --build
      - name: Run Frontend Tests
        run: |
          cd frontend && npm test -- --coverage
```

### 2. Environment Configuration
```bash
# Create proper .env templates
cp .env.example .env.local
cp .env.example .env.production
```

### 3. Monitoring & Logging
```python
# Add proper logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'team_planner.log',
        },
    },
    'loggers': {
        'team_planner': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🔐 Security Enhancements

### 1. Authentication & Authorization
```python
# Implement proper permission classes
class IsShiftManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('shifts.manage_shifts')
```

### 2. Input Validation
```python
# Add proper serializer validation
class ShiftSerializer(serializers.ModelSerializer):
    def validate_start_datetime(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Start time cannot be in the past")
        return value
```

### 3. Rate Limiting
```python
# Add rate limiting for API endpoints
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '100/hour'
    }
}
```
