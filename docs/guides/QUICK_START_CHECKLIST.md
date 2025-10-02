# Team Planner - Quick Start Checklist

## 🚀 SETUP CHECKLIST (30 minutes)

### Phase 1: Environment Setup ✅
```bash
# 1. Set environment variables
export DATABASE_URL=sqlite:///db.sqlite3
export DJANGO_SETTINGS_MODULE=config.settings.local
export DJANGO_SECRET_KEY=your-secret-key-here
export DJANGO_DEBUG=True

# 2. Verify Django works
python3 manage.py check
# Expected: "System check identified no issues (0 silenced)."

# 3. Setup database
python3 manage.py migrate
python3 manage.py createsuperuser
# Username: admin, Password: AdminPassword123!
```

### Phase 2: Fix Core Issues ✅
```bash
# 4. Run the automated setup script
python3 debug_and_setup.py
# This script will:
# - Create sample employees (8 users)
# - Assign proper skills (incidents, waakdienst)
# - Create test users with API tokens
# - Test availability detection
# - Test schedule generation
```

### Phase 3: Verify Functionality ✅
```bash
# 5. Run targeted tests
python3 manage.py test team_planner.orchestrators.tests.ConstraintCheckerTestCase.test_get_available_employees_incidents -v 2

# 6. Run full test suite
python3 manage.py test --verbosity=2
# Target: 90%+ pass rate (up from 74%)

# 7. Start servers
python3 manage.py runserver  # Backend on :8000
cd frontend && npm run dev   # Frontend on :5173
```

## 🎯 CRITICAL FIXES NEEDED

### Issue #1: Employee Availability Detection
**Problem**: No employees detected as available for shifts
**Test**: `ConstraintCheckerTestCase.test_get_available_employees_*`
**Fix**: Run `debug_and_setup.py` script

### Issue #2: API Authentication  
**Problem**: API tests failing with authentication errors
**Test**: `OrchestrationAPITestCase.*`
**Fix**: Test users created by setup script

### Issue #3: Schedule Generation
**Problem**: Orchestrators generate 0 shifts
**Test**: `ShiftOrchestratorTestCase.test_preview_schedule_basic`
**Fix**: Employee skills assignment

## 🧪 VALIDATION TESTS

After setup, these should all work:

```bash
# Test 1: Check employee skills
python3 manage.py shell
>>> from team_planner.employees.models import EmployeeProfile
>>> for p in EmployeeProfile.objects.all()[:3]:
...     print(f"{p.user.username}: {[s.name for s in p.skills.all()]}")
# Expected: Users should have "incidents" and/or "waakdienst" skills

# Test 2: Test API with token (get token from setup script output)
curl -H "Authorization: Token YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/orchestrator-status/health/
# Expected: {"status": "healthy", ...}

# Test 3: Generate simple schedule
python3 manage.py shell
>>> from team_planner.orchestrators.algorithms import generate_schedule
>>> from team_planner.teams.models import Team
>>> from datetime import datetime, timedelta
>>> import zoneinfo
>>> team = Team.objects.first()
>>> tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
>>> start = datetime(2025, 10, 7, tzinfo=tz)
>>> end = start + timedelta(days=7)
>>> result = generate_schedule(team, start, end, {'incidents': True}, preview_mode=True)
>>> print(f"Generated {result.get('total_shifts', 0)} shifts")
# Expected: > 0 shifts generated
```

## 🚨 TROUBLESHOOTING

### "No module named 'team_planner'"
```bash
cd /home/vscode/team_planner  # Ensure you're in project root
export PYTHONPATH=/home/vscode/team_planner:$PYTHONPATH
```

### "DATABASE_URL not set"
```bash
export DATABASE_URL=sqlite:///db.sqlite3
```

### "No employees available for shifts"
```bash
python3 debug_and_setup.py  # Re-run setup script
```

### ESLint errors in frontend
```bash
cd frontend
npm install @typescript-eslint/eslint-plugin @typescript-eslint/parser --save-dev
```

## 📊 SUCCESS METRICS

✅ **SETUP COMPLETE** when you see:
- [ ] Django check passes with no issues
- [ ] Database has 8+ employee profiles with skills
- [ ] At least 3 orchestrator tests pass
- [ ] API returns successful health check
- [ ] Schedule generation produces > 0 shifts
- [ ] Frontend runs without errors

✅ **DEVELOPMENT READY** when you have:
- [ ] 90%+ test pass rate
- [ ] Working employee availability detection  
- [ ] Functional API authentication
- [ ] Basic schedule generation working
- [ ] Frontend-backend integration

## 🔄 DAILY WORKFLOW

```bash
# Start development session
cd /home/vscode/team_planner
export DATABASE_URL=sqlite:///db.sqlite3
export DJANGO_SETTINGS_MODULE=config.settings.local

# Run tests
python3 manage.py test

# Start servers (2 terminals)
python3 manage.py runserver           # Terminal 1
cd frontend && npm run dev            # Terminal 2

# Make changes, run specific tests
python3 manage.py test team_planner.orchestrators.tests.ConstraintCheckerTestCase -v 2
```

## 📖 DOCUMENTATION

- **Complete Setup**: `DEVELOPMENT_SETUP_GUIDE.md`
- **Project Roadmap**: `STRATEGIC_ROADMAP.md`
- **Cleanup Report**: `PROJECT_CLEANUP_REPORT.md`
- **Test Analysis**: `TESTING_SUMMARY.md`

## 🎯 NEXT DEVELOPMENT PRIORITIES

1. **Fix remaining test failures** (orchestrator logic)
2. **Improve fairness calculations** 
3. **Add UI for employee skill management**
4. **Implement real-time schedule updates**
5. **Performance optimization**

---

**🎉 You're ready to start development!** 

This checklist gets you from cleaned code to working system in 30 minutes. The automated setup script handles the critical fixes, and the validation tests confirm everything works.
