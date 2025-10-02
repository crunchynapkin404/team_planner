# Reports & Exports - Quick Reference

## 📍 Access

**Frontend:** http://localhost:3000/reports  
**Backend API:** http://localhost:8000/api/reports/

## 🔐 Permissions Required

- Administrators (all permissions)
- Managers (`can_manage_team`)
- Shift Planners (`can_run_orchestrator`)

## 📊 Available Reports

### 1. Schedule Report
**Endpoint:** `GET /api/reports/schedule/`  
**Purpose:** View all shifts for a date range  
**Filters:** `start_date`, `end_date`, `team_id`, `department_id`

### 2. Fairness Distribution  
**Endpoint:** `GET /api/reports/fairness/`  
**Purpose:** Analyze shift distribution equity  
**Filters:** `start_date`, `end_date`, `team_id`

### 3. Leave Balance
**Endpoint:** `GET /api/reports/leave-balance/`  
**Purpose:** Track employee leave balances  
**Filters:** `employee_id`, `team_id`, `year`

### 4. Swap History
**Endpoint:** `GET /api/reports/swap-history/`  
**Purpose:** Audit shift swap requests  
**Filters:** `start_date`, `end_date`, `employee_id`, `team_id`

### 5. Employee Hours
**Endpoint:** `GET /api/reports/employee-hours/`  
**Purpose:** Track hours worked  
**Filters:** `start_date`, `end_date`, `employee_id`, `team_id`

### 6. Weekend/Holiday Distribution
**Endpoint:** `GET /api/reports/weekend-holiday/`  
**Purpose:** Analyze special shift fairness  
**Filters:** `start_date`, `end_date`, `team_id`

## 🧪 Quick Test

```bash
# Get your token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.token')

# Test schedule report
curl -H "Authorization: Token $TOKEN" \
  "http://localhost:8000/api/reports/schedule/?start_date=2025-10-01&end_date=2025-10-07" \
  | jq '.'

# Test fairness report
curl -H "Authorization: Token $TOKEN" \
  "http://localhost:8000/api/reports/fairness/" \
  | jq '.'
```

## 📝 Common Use Cases

### Weekly Schedule Review
1. Go to Reports → Schedule tab
2. Set current week dates
3. Select your team
4. Generate report

### Fairness Check
1. Go to Reports → Fairness tab
2. Set last 4 weeks
3. Select team
4. Check variance < 10 hours

### Leave Planning
1. Go to Reports → Leave Balance tab
2. Set current year
3. Filter by team
4. Identify low balances

## 🔧 Troubleshooting

**403 Forbidden:** Check you have required permissions  
**401 Unauthorized:** Ensure you're logged in  
**No data:** Verify date range and filters  
**Loading forever:** Check network tab for errors

## 📚 Documentation

- Full Guide: `WEEK_7-8_REPORTS_COMPLETE.md`
- Session Summary: `SESSION_SUMMARY_OCT_2_2025.md`
- Roadmap: `PROJECT_ROADMAP.md`
