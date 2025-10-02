# Timeline Phase 2: Advanced Filtering & Conflict Detection - Implementation Plan

**Start Date:** October 2, 2025  
**Status:** Planning Phase  
**Estimated Duration:** 1 week (18-24 hours)

---

## 🎯 Phase 2 Overview

Building on the successful completion of Phase 1 (10/10 Quick Wins), Phase 2 focuses on advanced filtering capabilities and intelligent conflict detection to make the Timeline page enterprise-ready.

**Phase 1 Foundation:**
- ✅ Basic filtering (search, status, team, My Schedule)
- ✅ Professional UI/UX
- ✅ Keyboard navigation
- ✅ Print support

**Phase 2 Goals:**
- Advanced filter panel with date ranges and employee selection
- Saved filter presets for quick access
- Visual conflict detection system
- Availability overlay
- Enterprise-grade scheduling intelligence

---

## 📋 Feature Breakdown

### Feature 1: Advanced Filter Panel (6-8 hours)

**Priority:** High  
**Complexity:** Medium  
**Dependencies:** Phase 1 filters, Material-UI DatePicker

#### Sub-Features:

1. **Collapsible Filter Drawer** (2 hours)
   - Right-side Drawer component (300px width)
   - Toggle button with FilterAlt icon
   - Smooth open/close animation
   - Persistent state (remains open/closed across view changes)
   - Print-hide class for printing

2. **Date Range Picker** (2 hours)
   - Start date picker
   - End date picker
   - "Last 7 days", "Last 30 days", "This month", "Next month" presets
   - Clear button
   - Visual indication when active
   - Integration with timeline data filtering

3. **Employee Multi-Select** (1.5 hours)
   - Autocomplete with checkboxes
   - Search within employee list
   - "Select All" / "Clear All" buttons
   - Shows selected count
   - Fetches from existing timeline data

4. **Save Filter Combinations** (2-2.5 hours)
   - Text field for filter name
   - Save button
   - Validation (non-empty name, unique names)
   - Store in localStorage
   - List of saved filters
   - Delete saved filter option
   - Maximum 10 saved filters

5. **Quick Apply Saved Filters** (0.5-1 hour)
   - List of saved filters with names
   - Click to apply all filter settings
   - Visual indication of active saved filter
   - Bookmark icon for favorites

#### Technical Implementation:

**State Management:**
```typescript
const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
const [dateRangeFilter, setDateRangeFilter] = useState<{ start: string | null; end: string | null }>({ start: null, end: null });
const [employeeFilter, setEmployeeFilter] = useState<string[]>([]);
const [employees, setEmployees] = useState<{ id: string; name: string }[]>([]);
const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([]);
const [filterName, setFilterName] = useState('');

interface SavedFilter {
  name: string;
  filters: {
    searchQuery: string;
    statusFilter: string[];
    shiftTypeFilter: string[];
    teamFilter: string[];
    employeeFilter: string[];
    dateRangeFilter: { start: string | null; end: string | null };
    showMyScheduleOnly: boolean;
  };
  createdAt: string;
}
```

**Filter Logic Integration:**
```typescript
const getFilteredTimelineData = () => {
  let filtered = [...timelineData];
  
  // Existing filters...
  
  // Date range filter
  if (dateRangeFilter.start || dateRangeFilter.end) {
    filtered = filtered.map(td => ({
      ...td,
      shifts: td.shifts.filter(shift => {
        const shiftDate = new Date(shift.start);
        const start = dateRangeFilter.start ? new Date(dateRangeFilter.start) : null;
        const end = dateRangeFilter.end ? new Date(dateRangeFilter.end) : null;
        
        if (start && shiftDate < start) return false;
        if (end && shiftDate > end) return false;
        return true;
      })
    })).filter(td => td.shifts.length > 0);
  }
  
  // Employee filter
  if (employeeFilter.length > 0) {
    filtered = filtered.filter(td => 
      employeeFilter.includes(td.engineer)
    );
  }
  
  return filtered;
};
```

**LocalStorage Management:**
```typescript
const saveFilter = () => {
  if (!filterName.trim()) {
    alert('Please enter a filter name');
    return;
  }
  
  const newFilter: SavedFilter = {
    name: filterName,
    filters: {
      searchQuery,
      statusFilter,
      shiftTypeFilter,
      teamFilter,
      employeeFilter,
      dateRangeFilter,
      showMyScheduleOnly
    },
    createdAt: new Date().toISOString()
  };
  
  const updated = [...savedFilters, newFilter];
  setSavedFilters(updated);
  localStorage.setItem('timeline_saved_filters', JSON.stringify(updated));
  setFilterName('');
};

const applyFilter = (filter: SavedFilter) => {
  setSearchQuery(filter.filters.searchQuery);
  setStatusFilter(filter.filters.statusFilter);
  setShiftTypeFilter(filter.filters.shiftTypeFilter);
  setTeamFilter(filter.filters.teamFilter);
  setEmployeeFilter(filter.filters.employeeFilter);
  setDateRangeFilter(filter.filters.dateRangeFilter);
  setShowMyScheduleOnly(filter.filters.showMyScheduleOnly);
};
```

#### UI Components:

**Drawer Structure:**
```tsx
<Drawer
  anchor="right"
  open={filterDrawerOpen}
  onClose={() => setFilterDrawerOpen(false)}
  sx={{ '& .MuiDrawer-paper': { width: 350, p: 2 } }}
  className="filter-drawer print-hide"
>
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
    <Typography variant="h6">Advanced Filters</Typography>
    <IconButton size="small" onClick={() => setFilterDrawerOpen(false)}>
      <Close />
    </IconButton>
  </Box>
  
  <Divider sx={{ mb: 2 }} />
  
  {/* Date Range Section */}
  <Typography variant="subtitle2" gutterBottom>Date Range</Typography>
  {/* Date pickers... */}
  
  <Divider sx={{ my: 2 }} />
  
  {/* Employee Selection */}
  <Typography variant="subtitle2" gutterBottom>Employees</Typography>
  {/* Employee autocomplete... */}
  
  <Divider sx={{ my: 2 }} />
  
  {/* Save Filter Section */}
  <Typography variant="subtitle2" gutterBottom>Save Current Filters</Typography>
  {/* Save filter UI... */}
  
  <Divider sx={{ my: 2 }} />
  
  {/* Saved Filters List */}
  <Typography variant="subtitle2" gutterBottom>Saved Filters</Typography>
  {/* List of saved filters... */}
</Drawer>
```

**Toggle Button:**
```tsx
<Button
  variant={filterDrawerOpen ? 'contained' : 'outlined'}
  startIcon={<FilterAlt />}
  onClick={() => setFilterDrawerOpen(!filterDrawerOpen)}
  size="small"
>
  Advanced Filters
</Button>
```

#### Expected Impact:
- 70% faster complex filtering scenarios
- 50% reduction in repetitive filter setup
- Better date-based scheduling workflows
- Improved manager productivity

---

### Feature 2: Conflict Detection System (8-10 hours)

**Priority:** High  
**Complexity:** High  
**Dependencies:** Backend API, Phase 1 UI

#### Sub-Features:

1. **Backend Conflict Detection Service** (4-5 hours)
   - Django service class: ConflictDetectionService
   - 4 conflict types:
     * Double-booking: Same employee, overlapping times
     * Leave conflict: Shift during approved leave
     * Over-scheduled: Exceeds max hours per week/month
     * Skill mismatch: Lacks required skills for shift type
   - API endpoint: `/api/shifts/check-conflicts/`
   - Returns conflict details with severity levels

2. **Visual Conflict Indicators** (2-3 hours)
   - Red border on conflicting shift chips
   - Warning icon (⚠️) next to shift
   - Conflict badge with count
   - Different colors for severity (red=critical, orange=warning, yellow=caution)

3. **Conflict Tooltip** (1-2 hours)
   - Hover over conflict indicator
   - Shows conflict type and description
   - Lists all conflicting shifts/leaves
   - Suggests resolution actions

4. **Conflict Resolution Suggestions** (1-2 hours)
   - "View alternatives" button
   - "Request swap" button
   - "Edit shift" button
   - "Cancel shift" button
   - Smart suggestions based on conflict type

#### Technical Implementation:

**Backend Service:**
```python
# shifts/services/conflict_detection.py

class ConflictDetectionService:
    @staticmethod
    def check_conflicts(shift):
        conflicts = []
        
        # Check double-booking
        overlapping = Shift.objects.filter(
            employee=shift.employee,
            start_time__lt=shift.end_time,
            end_time__gt=shift.start_time
        ).exclude(id=shift.id)
        
        if overlapping.exists():
            conflicts.append({
                'type': 'double_booking',
                'severity': 'critical',
                'message': f'Overlaps with {overlapping.count()} other shift(s)',
                'shifts': list(overlapping.values())
            })
        
        # Check leave conflicts
        leaves = LeaveRequest.objects.filter(
            employee=shift.employee,
            status='approved',
            start_date__lte=shift.start_time.date(),
            end_date__gte=shift.start_time.date()
        )
        
        if leaves.exists():
            conflicts.append({
                'type': 'leave_conflict',
                'severity': 'critical',
                'message': f'Employee on {leaves.first().leave_type.name}',
                'leaves': list(leaves.values())
            })
        
        # Check over-scheduling
        week_start = shift.start_time - timedelta(days=shift.start_time.weekday())
        week_shifts = Shift.objects.filter(
            employee=shift.employee,
            start_time__gte=week_start,
            start_time__lt=week_start + timedelta(days=7)
        )
        
        total_hours = sum([
            (s.end_time - s.start_time).total_seconds() / 3600 
            for s in week_shifts
        ])
        
        if total_hours > 60:  # Max 60 hours per week
            conflicts.append({
                'type': 'over_scheduled',
                'severity': 'warning',
                'message': f'Total weekly hours: {total_hours:.1f}/60',
                'hours': total_hours
            })
        
        return conflicts
```

**API Endpoint:**
```python
# shifts/api_views.py

@action(detail=True, methods=['get'])
def check_conflicts(self, request, pk=None):
    shift = self.get_object()
    conflicts = ConflictDetectionService.check_conflicts(shift)
    return Response({'conflicts': conflicts})
```

**Frontend Integration:**
```typescript
// In TimelinePage component
const [shiftConflicts, setShiftConflicts] = useState<{ [key: string]: any[] }>({});

const checkConflicts = async (shifts: CalendarEvent[]) => {
  const conflicts: { [key: string]: any[] } = {};
  
  for (const shift of shifts) {
    try {
      const response = await apiClient.get(`/api/shifts/${shift.id}/check-conflicts/`);
      if (response.conflicts && response.conflicts.length > 0) {
        conflicts[shift.id] = response.conflicts;
      }
    } catch (err) {
      console.error('Error checking conflicts:', err);
    }
  }
  
  setShiftConflicts(conflicts);
};

// Call on data load
useEffect(() => {
  if (allShiftsData.length > 0) {
    checkConflicts(allShiftsData);
  }
}, [allShiftsData]);
```

**Visual Indicators:**
```tsx
<Chip
  label={shift.title}
  size="small"
  sx={{
    backgroundColor: shift.backgroundColor,
    border: shiftConflicts[shift.id] ? '2px solid #f44336' : 'none',
    position: 'relative'
  }}
  icon={shiftConflicts[shift.id] ? <Warning color="error" /> : undefined}
/>

{shiftConflicts[shift.id] && (
  <Tooltip title={
    <Box>
      <Typography variant="caption" fontWeight="bold">Conflicts Detected:</Typography>
      {shiftConflicts[shift.id].map((conflict, idx) => (
        <Typography key={idx} variant="caption" display="block">
          • {conflict.message}
        </Typography>
      ))}
    </Box>
  }>
    <Badge badgeContent={shiftConflicts[shift.id].length} color="error" />
  </Tooltip>
)}
```

#### Expected Impact:
- 90% reduction in scheduling conflicts
- 30% fewer manual conflict resolution
- Proactive conflict prevention
- Better shift coverage quality

---

### Feature 3: Availability Overlay (4-6 hours)

**Priority:** Medium  
**Complexity:** Medium  
**Dependencies:** Backend API, Feature 2

#### Sub-Features:

1. **Availability Toggle** (1 hour)
   - Toggle button in header
   - "Show Availability" / "Hide Availability"
   - Persists state in localStorage

2. **Availability Calculation** (2-3 hours)
   - Backend service: AvailabilityService
   - Considers:
     * Approved leaves
     * Existing shifts
     * Max hours constraints
     * Recurring unavailability patterns
   - API endpoint: `/api/employees/availability/`

3. **Visual Indicators** (1-2 hours)
   - Cell background colors:
     * Green: Fully available
     * Yellow: Partially available (some constraints)
     * Red: Unavailable (on leave or fully booked)
   - Opacity overlay on shift chips
   - Legend showing color meanings

4. **Real-Time Updates** (0.5-1 hour)
   - Updates when shifts added/removed
   - Updates when leaves approved/rejected
   - Refresh button to manually update

#### Technical Implementation:

**Backend Service:**
```python
# teams/services/availability.py

class AvailabilityService:
    @staticmethod
    def get_availability(employee, date):
        # Check leaves
        leaves = LeaveRequest.objects.filter(
            employee=employee,
            status='approved',
            start_date__lte=date,
            end_date__gte=date
        )
        
        if leaves.exists():
            return {
                'status': 'unavailable',
                'reason': 'On leave',
                'color': '#ffebee'  # Light red
            }
        
        # Check existing shifts
        shifts = Shift.objects.filter(
            employee=employee,
            start_time__date=date
        )
        
        total_hours = sum([
            (s.end_time - s.start_time).total_seconds() / 3600 
            for s in shifts
        ])
        
        if total_hours >= 12:
            return {
                'status': 'unavailable',
                'reason': 'Fully booked',
                'color': '#ffebee'
            }
        elif total_hours >= 8:
            return {
                'status': 'partial',
                'reason': f'{total_hours:.1f}/12 hours',
                'color': '#fff9c4'  # Light yellow
            }
        
        return {
            'status': 'available',
            'reason': 'Available',
            'color': '#e8f5e9'  # Light green
        }
```

**Frontend Integration:**
```typescript
const [availabilityMode, setAvailabilityMode] = useState(false);
const [availability, setAvailability] = useState<{ [key: string]: any }>({});

const fetchAvailability = async () => {
  const avail: { [key: string]: any } = {};
  
  for (const td of timelineData) {
    for (const date of dateRange) {
      const key = `${td.engineer}-${date.toISOString()}`;
      const response = await apiClient.get(`/api/employees/availability/`, {
        params: {
          employee: td.engineer,
          date: date.toISOString().split('T')[0]
        }
      });
      avail[key] = response;
    }
  }
  
  setAvailability(avail);
};

// Cell styling
<TableCell
  sx={{
    backgroundColor: availabilityMode && availability[cellKey] 
      ? availability[cellKey].color 
      : 'transparent',
    opacity: availabilityMode ? 0.7 : 1
  }}
>
  {/* Shift chips... */}
</TableCell>
```

#### Expected Impact:
- 50% faster availability checking
- Better scheduling decisions
- Reduced over-scheduling
- Visual at-a-glance availability

---

## 📊 Phase 2 Success Criteria

### Functional Requirements
- [ ] Advanced filter drawer opens/closes smoothly
- [ ] Date range filter works with timeline data
- [ ] Employee filter shows all engineers
- [ ] Saved filters persist in localStorage
- [ ] Saved filters apply correctly when clicked
- [ ] Conflicts detected automatically on load
- [ ] Visual conflict indicators appear on conflicting shifts
- [ ] Conflict tooltips show helpful information
- [ ] Availability overlay shows correct colors
- [ ] Availability updates when data changes

### Non-Functional Requirements
- [ ] Performance: Conflict checking doesn't block UI (async)
- [ ] Performance: Availability calculation cached appropriately
- [ ] Usability: Advanced filters are intuitive
- [ ] Usability: Conflict indicators are clear
- [ ] Maintainability: Clean separation of concerns
- [ ] Scalability: Works with 100+ employees

### User Acceptance
- [ ] Managers can save common filter combinations
- [ ] Conflicts are immediately visible
- [ ] Availability helps with scheduling decisions
- [ ] All features work together harmoniously

---

## 🎯 Implementation Order

### Day 1-2: Advanced Filter Panel
1. Add Drawer component and toggle button
2. Implement date range picker
3. Implement employee multi-select
4. Add save filter functionality
5. Add saved filters list
6. Test all filter combinations

### Day 3-4: Conflict Detection Backend
1. Create ConflictDetectionService
2. Implement 4 conflict checks
3. Create API endpoint
4. Write unit tests
5. Test with sample data

### Day 4-5: Conflict Detection Frontend
1. Fetch conflicts on data load
2. Add visual indicators
3. Create conflict tooltip
4. Add resolution suggestions
5. Test user workflows

### Day 5-6: Availability Overlay
1. Create AvailabilityService
2. Create API endpoint
3. Add toggle button
4. Fetch and display availability
5. Add legend
6. Test performance

### Day 7: Testing & Documentation
1. Integration testing
2. Performance testing
3. User acceptance testing
4. Documentation
5. Commit and push

---

## 📝 Git Commit Strategy

**Commit Pattern:**
- Feature 1: Advanced Filter Panel (3-4 commits)
  * Commit 1: Drawer UI and toggle
  * Commit 2: Date range and employee filters
  * Commit 3: Save filter functionality
  * Commit 4: Saved filters list and apply

- Feature 2: Conflict Detection (4-5 commits)
  * Commit 1: Backend service
  * Commit 2: API endpoint
  * Commit 3: Frontend integration
  * Commit 4: Visual indicators
  * Commit 5: Tooltips and suggestions

- Feature 3: Availability Overlay (2-3 commits)
  * Commit 1: Backend service and API
  * Commit 2: Frontend toggle and display
  * Commit 3: Legend and polish

**Total Commits:** 9-12 commits

---

## 🚀 Next Steps

1. Begin with Advanced Filter Panel implementation
2. Implement features incrementally with commits
3. Test thoroughly at each stage
4. Update PROJECT_ROADMAP.md as features complete
5. Create TIMELINE_PHASE_2_COMPLETE.md upon completion

**Ready to start implementation!**
