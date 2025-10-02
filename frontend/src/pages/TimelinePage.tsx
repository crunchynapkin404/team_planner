import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Paper,
  SelectChangeEvent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Divider,
  TextField,
  InputAdornment,
  Tooltip,
} from '@mui/material';
import {
  ChevronLeft,
  ChevronRight,
  Today,
  Close,
  Search,
  Clear,
  FilterList,
} from '@mui/icons-material';
import { apiClient } from '../services/apiClient';
import { API_CONFIG } from '../config/api';
import { CalendarEvent } from '../types/calendar';
import { formatDate } from '../utils/dateUtils';

interface TimelineData {
  engineer: string;
  shifts: CalendarEvent[];
  leaves: CalendarEvent[];
}

const TimelinePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'week' | 'month' | 'quarter' | 'year'>('month');
  const [timelineData, setTimelineData] = useState<TimelineData[]>([]);
  const [dateRange, setDateRange] = useState<Date[]>([]);
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [allShiftsData, setAllShiftsData] = useState<CalendarEvent[]>([]);
  const [allLeavesData, setAllLeavesData] = useState<CalendarEvent[]>([]);
  const [selectedShifts, setSelectedShifts] = useState<CalendarEvent[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  
  // Filter states
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [shiftTypeFilter, setShiftTypeFilter] = useState<string[]>([]);
  const [showMyScheduleOnly, setShowMyScheduleOnly] = useState(false);

    // Fetch recurring leave patterns and generate calendar events
  const fetchRecurringLeavePatterns = async (): Promise<CalendarEvent[]> => {
    console.log('🔍 Starting fetchRecurringLeavePatterns...');
    try {
      // Get current user info 
      console.log('📱 Fetching current user...');
      const userResponse = await apiClient.get('/api/users/me/') as any;
      const currentUser = userResponse.data;
      console.log('👤 Current user:', currentUser);
      
      // All users can see all patterns - we need to fetch all users' patterns
      console.log('👥 Fetching all users...');
      const usersResponse = await apiClient.get('/api/users/') as any;
      console.log('Users response:', usersResponse);
      
      // Extract users from paginated response
      let allUsers = [];
      console.log('🔍 Response structure analysis:', {
        hasData: !!usersResponse.data,
        hasResults: !!usersResponse.results,
        topLevelKeys: Object.keys(usersResponse),
        dataKeys: usersResponse.data ? Object.keys(usersResponse.data) : 'no data prop'
      });
      
      // The data is directly on usersResponse, not usersResponse.data
      if (usersResponse.results && Array.isArray(usersResponse.results)) {
        allUsers = usersResponse.results;
        console.log('✅ Extracted from usersResponse.results');
      } else if (usersResponse.data && usersResponse.data.results && Array.isArray(usersResponse.data.results)) {
        allUsers = usersResponse.data.results;
        console.log('✅ Extracted from usersResponse.data.results');
      } else if (Array.isArray(usersResponse)) {
        allUsers = usersResponse;
        console.log('✅ Used usersResponse directly as array');
      } else {
        console.log('❌ Could not extract users from response');
      }
      
      console.log('All users:', allUsers);
      
      if (allUsers.length === 0) {
        console.warn('⚠️ No users found!');
        return [];
      }
      
      const allPatterns: any[] = [];
      // Fetch patterns for each user
      console.log(`🔄 Fetching patterns for ${allUsers.length} users...`);
      for (const user of allUsers) {
        console.log(`🔍 Fetching patterns for user: ${user.username} (ID: ${user.id})`);
        try {
          const userPatternsResponse = await apiClient.get(`/api/users/${user.id}/recurring-leave-patterns/`) as any;
          console.log(`📋 Full patterns response for user ${user.username}:`, userPatternsResponse);
          console.log(`📋 Response structure:`, {
            hasData: !!userPatternsResponse.data,
            hasResults: !!userPatternsResponse.results,
            isArray: Array.isArray(userPatternsResponse),
            topKeys: Object.keys(userPatternsResponse)
          });
          
          // Try multiple access patterns for the response
          let patterns = null;
          if (userPatternsResponse.results && Array.isArray(userPatternsResponse.results)) {
            patterns = userPatternsResponse.results;
            console.log(`✅ Using userPatternsResponse.results (${patterns.length} patterns)`);
          } else if (userPatternsResponse.data && Array.isArray(userPatternsResponse.data)) {
            patterns = userPatternsResponse.data;
            console.log(`✅ Using userPatternsResponse.data (${patterns.length} patterns)`);
          } else if (Array.isArray(userPatternsResponse)) {
            patterns = userPatternsResponse;
            console.log(`✅ Using userPatternsResponse directly (${patterns.length} patterns)`);
          } else {
            console.log(`❌ No patterns found in response structure`);
          }
          
          if (patterns && Array.isArray(patterns)) {
            allPatterns.push(...patterns);
            console.log(`✅ Added ${patterns.length} patterns for ${user.username}`);
          }
        } catch (err) {
          // User might not have patterns or permission issues, skip
          console.warn(`❌ Error fetching patterns for user ${user.username}:`, err);
        }
      }
      console.log('📊 All patterns collected:', allPatterns);
      
      // If no patterns found from all users, try the original endpoint as fallback
      if (allPatterns.length === 0) {
        console.log('🔄 No patterns found from all users, trying fallback...');
        try {
          const fallbackResponse = await apiClient.get('/api/recurring-leave-patterns/') as any;
          console.log('📋 Fallback response:', fallbackResponse.data);
          if (fallbackResponse.data && Array.isArray(fallbackResponse.data)) {
            allPatterns.push(...fallbackResponse.data);
            console.log(`✅ Added ${fallbackResponse.data.length} patterns from fallback`);
          }
        } catch (fallbackErr) {
          console.error('❌ Fallback also failed:', fallbackErr);
        }
      }
      const patternsResponse = { data: allPatterns };
      
      console.log(`🎯 Processing ${allPatterns.length} patterns into calendar events...`);
      const recurringEvents: CalendarEvent[] = [];
      
      if (patternsResponse.data && Array.isArray(patternsResponse.data)) {
        for (const pattern of patternsResponse.data) {
          console.log('🔄 Processing pattern:', pattern);
          // Find the user object for this pattern's employee ID
          const patternOwner = allUsers.find((user: any) => user.id === pattern.employee) || currentUser;
          console.log('👤 Pattern owner:', patternOwner);
          const events = generateRecurringLeaveEvents(pattern, patternOwner);
          console.log(`📅 Generated ${events.length} events for pattern ${pattern.id}`);
          recurringEvents.push(...events);
        }
      }
      
      console.log(`✅ Total recurring events generated: ${recurringEvents.length}`);
      return recurringEvents;
    } catch (err) {
      console.error('❌ Failed to fetch recurring leave patterns:', err);
      return [];
    }
  };

  // Generate calendar events from a recurring leave pattern
  const generateRecurringLeaveEvents = (pattern: any, user: any): CalendarEvent[] => {
    const events: CalendarEvent[] = [];
    
    const today = new Date();
    const effectiveFrom = new Date(pattern.effective_from);
    const effectiveUntil = pattern.effective_until ? new Date(pattern.effective_until) : new Date(today.getFullYear() + 1, today.getMonth(), today.getDate());
    const patternStartDate = new Date(pattern.pattern_start_date);
    
    // Get engineer name from user data
    let engineerName = user.display_name;
    if (user.first_name && user.last_name) {
      engineerName = `${user.first_name} ${user.last_name}`;
    } else if (user.display_name && user.display_name !== user.username) {
      engineerName = user.display_name;
    } else {
      const username = user.username || user.display_name;
      if (username && username.includes('.')) {
        engineerName = username.split('.').map((part: string) => 
          part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()
        ).join(' ');
      } else {
        engineerName = username;
      }
    }
    
    // Calculate occurrence dates
    let currentDate = new Date(Math.max(effectiveFrom.getTime(), patternStartDate.getTime()));
    
    // Adjust to the correct day of week
    const dayOfWeek = pattern.day_of_week; // 0 = Monday, 1 = Tuesday, etc.
    const currentDayOfWeek = (currentDate.getDay() + 6) % 7; // Convert Sunday=0 to Monday=0
    const daysToAdd = (dayOfWeek - currentDayOfWeek + 7) % 7;
    currentDate.setDate(currentDate.getDate() + daysToAdd);
    
    // Generate events up to effective_until date
    while (currentDate <= effectiveUntil) {
      // Check if this date should be included based on frequency
      const shouldInclude = pattern.frequency === 'weekly' || 
        (pattern.frequency === 'biweekly' && 
         Math.floor((currentDate.getTime() - patternStartDate.getTime()) / (1000 * 60 * 60 * 24 * 7)) % 2 === 0);
      
      if (shouldInclude && currentDate >= effectiveFrom) {
        const eventDate = new Date(currentDate);
        
        // Create event based on coverage type
        let startTime = new Date(eventDate);
        let endTime = new Date(eventDate);
        
        switch (pattern.coverage_type) {
          case 'morning':
            startTime.setHours(8, 0, 0, 0);
            endTime.setHours(12, 0, 0, 0);
            break;
          case 'afternoon':
            startTime.setHours(12, 0, 0, 0);
            endTime.setHours(17, 0, 0, 0);
            break;
          case 'full_day':
          default:
            startTime.setHours(8, 0, 0, 0);
            endTime.setHours(17, 0, 0, 0);
            break;
        }
        
        const event: CalendarEvent = {
          id: `recurring-${pattern.id}-${eventDate.toISOString().split('T')[0]}`,
          title: `${pattern.name} (Recurring)`,
          start: startTime.toISOString().split('T')[0],
          end: endTime.toISOString().split('T')[0],
          backgroundColor: '#2e7d32', // Green for approved/recurring leave
          borderColor: '#2e7d32',
          extendedProps: {
            eventType: 'leave' as const,
            engineerName: engineerName,
            engineerId: user.id.toString(),
            status: 'approved',
            reason: pattern.notes || 'Recurring leave pattern',
            days_requested: pattern.coverage_type === 'full_day' ? 1 : 0.5,
            leave_type_name: pattern.name,
            leave_type_color: '#2e7d32',
            isRecurring: true,
            recurringPatternId: pattern.id,
            coverage_type: pattern.coverage_type,
          }
        };
        
        events.push(event);
      }
      
      // Move to next week
      currentDate.setDate(currentDate.getDate() + 7);
    }
    
    return events;
  };

  // Fetch shifts and leave requests from API
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch shifts
      const shiftsResponse = await apiClient.get(API_CONFIG.ENDPOINTS.SHIFTS_LIST);
      const shiftsData = shiftsResponse as { events: CalendarEvent[] };
      
      // Fetch leave requests
      const leavesResponse = await apiClient.get(API_CONFIG.ENDPOINTS.LEAVES_REQUESTS);
      const leavesData = leavesResponse as { results: any[] };
      
      // Fetch recurring leave patterns
      console.log('🔄 Fetching recurring leave patterns...');
      const recurringPatternsEvents = await fetchRecurringLeavePatterns();
      console.log('📋 Recurring patterns events received:', recurringPatternsEvents);
      
      // Convert leave requests to calendar events
      const leaveEvents: CalendarEvent[] = leavesData.results.map((leave: any) => {
        // Try to get a proper display name - check if first_name and last_name exist and are not null
        let engineerName = leave.employee.display_name;
        
        if (leave.employee.first_name && leave.employee.last_name) {
          // Use first_name + last_name if both are available
          engineerName = `${leave.employee.first_name} ${leave.employee.last_name}`;
        } else if (leave.employee.display_name && leave.employee.display_name !== leave.employee.username) {
          // Use display_name if it's different from username (meaning it's a proper name)
          engineerName = leave.employee.display_name;
        } else {
          // Fallback: try to format the username nicely
          const username = leave.employee.username || leave.employee.display_name;
          if (username && username.includes('.')) {
            // Convert "bart.abraas" to "Bart Abraas"
            engineerName = username.split('.').map((part: string) => 
              part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()
            ).join(' ');
          } else {
            engineerName = username;
          }
        }
        
        return {
          id: `leave-${leave.id}`,
          title: `${leave.leave_type.name} (${leave.status})`,
          start: leave.start_date,
          end: leave.end_date,
          backgroundColor: getLeaveColor(leave.status, leave.leave_type.color),
          borderColor: getLeaveColor(leave.status, leave.leave_type.color),
          extendedProps: {
            eventType: 'leave' as const,
            engineerName: engineerName,
            engineerId: leave.employee.id.toString(),
            status: leave.status,
            reason: leave.reason,
            days_requested: leave.days_requested,
            leave_type_name: leave.leave_type.name,
            leave_type_color: leave.leave_type.color,
          }
        };
      });
      
      // Combine regular leave events with recurring pattern events
      const allLeaveEvents = [...leaveEvents, ...recurringPatternsEvents];
      
      setAllShiftsData(shiftsData.events);
      setAllLeavesData(allLeaveEvents);
      
      // Use today's date for initial processing
      const today = new Date();
      processTimelineData(shiftsData.events, allLeaveEvents, today);
    } catch (err) {
      setError('Failed to load data');
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to get color based on leave status
  const getLeaveColor = (status: string, _leaveTypeColor?: string) => {
    switch (status) {
      case 'approved':
        return '#2e7d32'; // Darker green for approved (different from incidents_standby)
      case 'pending':
        return '#e65100'; // Dark orange for pending
      case 'rejected':
        return '#f44336'; // Red for rejected
      case 'cancelled':
        return '#9e9e9e'; // Grey for cancelled
      default:
        return '#2196f3'; // Blue as default
    }
  };

  // Generate date range based on view mode and current date
  const generateDateRange = (baseDate: Date, mode: 'week' | 'month' | 'quarter' | 'year'): Date[] => {
    const dates: Date[] = [];
    let startDate: Date;
    let endDate: Date;
    
    switch (mode) {
      case 'week':
        // Start from Monday of the week containing baseDate
        startDate = new Date(baseDate);
        startDate.setDate(startDate.getDate() - (startDate.getDay() || 7) + 1);
        endDate = new Date(startDate);
        endDate.setDate(endDate.getDate() + 6);
        break;
        
      case 'month':
        // Start from today and show next 30 days
        startDate = new Date(baseDate);
        endDate = new Date(baseDate);
        endDate.setDate(endDate.getDate() + 30);
        break;
        
      case 'quarter':
        // Start from today and show next 90 days
        startDate = new Date(baseDate);
        endDate = new Date(baseDate);
        endDate.setDate(endDate.getDate() + 90);
        break;
        
      case 'year':
        // Start from today and show next 365 days
        startDate = new Date(baseDate);
        endDate = new Date(baseDate);
        endDate.setDate(endDate.getDate() + 365);
        break;
        
      default:
        startDate = new Date(baseDate);
        endDate = new Date(baseDate);
    }
    
    const current = new Date(startDate);
    while (current <= endDate) {
      dates.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    
    return dates;
  };

  // Get current user for "My Schedule" filter
  const getCurrentUser = () => {
    try {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        const user = JSON.parse(userStr);
        return user.username || user.email || '';
      }
    } catch (error) {
      console.error('Error getting current user:', error);
    }
    return '';
  };

  // Filter timeline data based on search and filters
  const getFilteredTimelineData = () => {
    let filtered = [...timelineData];
    
    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(td => 
        td.engineer.toLowerCase().includes(query)
      );
    }
    
    // Apply "My Schedule" filter
    if (showMyScheduleOnly) {
      const currentUser = getCurrentUser();
      filtered = filtered.filter(td => 
        td.engineer.toLowerCase() === currentUser.toLowerCase()
      );
    }
    
    // Apply status filter (filter shifts within each engineer's data)
    if (statusFilter.length > 0) {
      filtered = filtered.map(td => ({
        ...td,
        shifts: td.shifts.filter(shift => 
          statusFilter.includes(shift.extendedProps?.status || 'scheduled')
        )
      })).filter(td => td.shifts.length > 0 || td.leaves.length > 0);
    }
    
    // Apply shift type filter
    if (shiftTypeFilter.length > 0) {
      filtered = filtered.map(td => ({
        ...td,
        shifts: td.shifts.filter(shift => 
          shiftTypeFilter.includes(shift.extendedProps?.shiftType || '')
        )
      })).filter(td => td.shifts.length > 0 || td.leaves.length > 0);
    }
    
    return filtered;
  };

  // Process shifts and leaves into timeline format
  const processTimelineData = (shiftsData: CalendarEvent[], leavesData: CalendarEvent[], baseDate?: Date) => {
    // Group shifts by engineer
    const shiftGroups: { [key: string]: CalendarEvent[] } = {};
    shiftsData.forEach((shift) => {
      const engineerName = shift.extendedProps?.engineerName || 'Unassigned';
      if (!shiftGroups[engineerName]) {
        shiftGroups[engineerName] = [];
      }
      shiftGroups[engineerName].push(shift);
    });

    // Group leaves by engineer
    const leaveGroups: { [key: string]: CalendarEvent[] } = {};
    leavesData.forEach((leave) => {
      const engineerName = leave.extendedProps?.engineerName || 'Unassigned';
      if (!leaveGroups[engineerName]) {
        leaveGroups[engineerName] = [];
      }
      leaveGroups[engineerName].push(leave);
    });

    // Get all unique engineers from both shifts and leaves
    const allEngineers = new Set([
      ...Object.keys(shiftGroups),
      ...Object.keys(leaveGroups)
    ]);

    // Convert to timeline data
    const timeline: TimelineData[] = Array.from(allEngineers)
      .map((engineer) => ({
        engineer,
        shifts: shiftGroups[engineer] || [],
        leaves: leaveGroups[engineer] || []
      }))
      .sort((a, b) => a.engineer.localeCompare(b.engineer));

    setTimelineData(timeline);

    // Generate date range based on current view mode and date
    const dateToUse = baseDate || currentDate;
    const dates = generateDateRange(dateToUse, viewMode);
    setDateRange(dates);
  };

  // Get shifts for a specific engineer and date, grouped by shift type
  const getShiftsForEngineerAndDate = (engineer: string, date: Date): CalendarEvent[] => {
    const engineerData = timelineData.find(td => td.engineer === engineer);
    if (!engineerData) return [];
    
    return engineerData.shifts.filter(shift => {
      const shiftStart = new Date(shift.start);
      const shiftEnd = new Date(shift.end);
      const dayStart = new Date(date);
      dayStart.setHours(0, 0, 0, 0);
      const dayEnd = new Date(date);
      dayEnd.setHours(23, 59, 59, 999);
      
      // Check if shift overlaps with this day
      return shiftStart <= dayEnd && shiftEnd >= dayStart;
    });
  };

  // Get leaves for a specific engineer and date
  const getLeavesForEngineerAndDate = (engineer: string, date: Date): CalendarEvent[] => {
    const engineerData = timelineData.find(td => td.engineer === engineer);
    if (!engineerData) return [];
    
    return engineerData.leaves.filter(leave => {
      const leaveStart = new Date(leave.start);
      const leaveEnd = new Date(leave.end);
      const dayStart = new Date(date);
      dayStart.setHours(0, 0, 0, 0);
      const dayEnd = new Date(date);
      dayEnd.setHours(23, 59, 59, 999);
      
      // Check if leave overlaps with this day
      return leaveStart <= dayEnd && leaveEnd >= dayStart;
    });
  };

  // Group shifts by type for the same day
  const groupShiftsByType = (shifts: CalendarEvent[]) => {
    const grouped: { [key: string]: CalendarEvent[] } = {};
    
    shifts.forEach(shift => {
      const shiftType = shift.extendedProps?.shiftType || 'unknown';
      if (!grouped[shiftType]) {
        grouped[shiftType] = [];
      }
      grouped[shiftType].push(shift);
    });
    
    return grouped;
  };

  // Get color for shift type
  const getShiftColor = (shiftType: string) => {
    switch (shiftType.toLowerCase()) {
      case 'incident':
      case 'incidents':
        return '#2196f3'; // Blue
      case 'incidents-standby':
      case 'incident-standby':
      case 'incidents_standby':
      case 'incident_standby':
        return '#ff9800'; // Orange
      case 'waakdienst':
        return '#9c27b0'; // Purple
      case 'project':
        return '#ff9800'; // Orange
      case 'change':
        return '#f44336'; // Red
      default:
        return '#4caf50'; // Green for unknown
    }
  };

  // Format shift type for display
  const formatShiftType = (shiftType: string) => {
    return shiftType
      .replace(/_/g, ' ')           // Replace underscores with spaces
      .replace(/-/g, ' ')           // Replace hyphens with spaces
      .replace(/\b\w/g, l => l.toUpperCase()); // Capitalize first letter of each word
  };

  // Handle view mode change
  const handleViewModeChange = (event: SelectChangeEvent) => {
    const newMode = event.target.value as 'week' | 'month' | 'quarter' | 'year';
    setViewMode(newMode);
    // Regenerate date range with new view mode
    const dates = generateDateRange(currentDate, newMode);
    setDateRange(dates);
  };

  // Navigation functions
  const navigatePrevious = () => {
    const newDate = new Date(currentDate);
    switch (viewMode) {
      case 'week':
        newDate.setDate(newDate.getDate() - 7);
        break;
      case 'month':
        newDate.setMonth(newDate.getMonth() - 1);
        break;
      case 'quarter':
        newDate.setMonth(newDate.getMonth() - 3);
        break;
      case 'year':
        newDate.setFullYear(newDate.getFullYear() - 1);
        break;
    }
    setCurrentDate(newDate);
    const dates = generateDateRange(newDate, viewMode);
    setDateRange(dates);
  };

  const navigateNext = () => {
    const newDate = new Date(currentDate);
    switch (viewMode) {
      case 'week':
        newDate.setDate(newDate.getDate() + 7);
        break;
      case 'month':
        newDate.setMonth(newDate.getMonth() + 1);
        break;
      case 'quarter':
        newDate.setMonth(newDate.getMonth() + 3);
        break;
      case 'year':
        newDate.setFullYear(newDate.getFullYear() + 1);
        break;
    }
    setCurrentDate(newDate);
    const dates = generateDateRange(newDate, viewMode);
    setDateRange(dates);
  };

  const goToToday = () => {
    const today = new Date();
    setCurrentDate(today);
    const dates = generateDateRange(today, viewMode);
    setDateRange(dates);
  };

  // Get period label for display
  const getPeriodLabel = () => {
    switch (viewMode) {
      case 'week':
        const weekStart = new Date(currentDate);
        weekStart.setDate(weekStart.getDate() - (weekStart.getDay() || 7) + 1);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekEnd.getDate() + 6);
        return `${formatDate(weekStart)} - ${formatDate(weekEnd)}`;
      case 'month':
        const monthEnd = new Date(currentDate);
        monthEnd.setDate(monthEnd.getDate() + 30);
        return `${formatDate(currentDate)} - ${formatDate(monthEnd)}`;
      case 'quarter':
        const quarterEnd = new Date(currentDate);
        quarterEnd.setDate(quarterEnd.getDate() + 90);
        return `${formatDate(currentDate)} - ${formatDate(quarterEnd)}`;
      case 'year':
        const yearEnd = new Date(currentDate);
        yearEnd.setDate(yearEnd.getDate() + 365);
        return `${formatDate(currentDate)} - ${formatDate(yearEnd)}`;
      default:
        return '';
    }
  };

  // Handle chip click to show shift details
  const handleChipClick = (shifts: CalendarEvent[]) => {
    setSelectedShifts(shifts);
    setDialogOpen(true);
  };

  // Close dialog
  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedShifts([]);
  };

  // Load data on component mount
  useEffect(() => {
    fetchData();
    // Set current date to today when component first loads
    const today = new Date();
    setCurrentDate(today);
  }, []);

  // Regenerate timeline when view mode or current date changes
  useEffect(() => {
    if (allShiftsData.length > 0 || allLeavesData.length > 0) {
      processTimelineData(allShiftsData, allLeavesData, currentDate);
    }
  }, [viewMode, currentDate, allShiftsData, allLeavesData]);

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Timeline View
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Resource timeline showing engineer schedules
        </Typography>
      </Box>

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* View Mode Selector */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>View Mode</InputLabel>
            <Select
              value={viewMode}
              label="View Mode"
              onChange={handleViewModeChange}
            >
              <MenuItem value="week">Week</MenuItem>
              <MenuItem value="month">Month</MenuItem>
              <MenuItem value="quarter">Quarter</MenuItem>
              <MenuItem value="year">Year</MenuItem>
            </Select>
          </FormControl>

          {/* Date Navigation */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton onClick={navigatePrevious} size="small">
              <ChevronLeft />
            </IconButton>
            
            <Typography variant="body1" sx={{ minWidth: 200, textAlign: 'center', fontWeight: 'bold' }}>
              {getPeriodLabel()}
            </Typography>
            
            <IconButton onClick={navigateNext} size="small">
              <ChevronRight />
            </IconButton>
          </Box>

          {/* Today Button */}
          <Button 
            variant="outlined" 
            size="small" 
            onClick={goToToday}
            startIcon={<Today />}
          >
            Today
          </Button>

          {/* Stats */}
          <Box sx={{ ml: 'auto' }}>
            <Typography variant="body2" color="text.secondary">
              {getFilteredTimelineData().length} engineers, {getFilteredTimelineData().reduce((sum, td) => sum + td.shifts.length, 0)} shifts
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Search Box */}
          <TextField
            size="small"
            placeholder="Search engineers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setSearchQuery('')}>
                    <Clear fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ),
            }}
            sx={{ minWidth: 250 }}
          />

          {/* My Schedule Toggle */}
          <Tooltip title={showMyScheduleOnly ? 'Show all schedules' : 'Show only my shifts'}>
            <Button
              size="small"
              variant={showMyScheduleOnly ? 'contained' : 'outlined'}
              onClick={() => setShowMyScheduleOnly(!showMyScheduleOnly)}
            >
              {showMyScheduleOnly ? '✓ My Schedule' : 'My Schedule'}
            </Button>
          </Tooltip>

          {/* Status Filters */}
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <FilterList fontSize="small" />
            <Chip
              label="All Status"
              size="small"
              color={statusFilter.length === 0 ? 'primary' : 'default'}
              onClick={() => setStatusFilter([])}
            />
            <Chip
              label="Confirmed"
              size="small"
              color={statusFilter.includes('confirmed') ? 'success' : 'default'}
              onClick={() => {
                if (statusFilter.includes('confirmed')) {
                  setStatusFilter(statusFilter.filter(s => s !== 'confirmed'));
                } else {
                  setStatusFilter([...statusFilter, 'confirmed']);
                }
              }}
            />
            <Chip
              label="Scheduled"
              size="small"
              color={statusFilter.includes('scheduled') ? 'primary' : 'default'}
              onClick={() => {
                if (statusFilter.includes('scheduled')) {
                  setStatusFilter(statusFilter.filter(s => s !== 'scheduled'));
                } else {
                  setStatusFilter([...statusFilter, 'scheduled']);
                }
              }}
            />
            <Chip
              label="Cancelled"
              size="small"
              color={statusFilter.includes('cancelled') ? 'error' : 'default'}
              onClick={() => {
                if (statusFilter.includes('cancelled')) {
                  setStatusFilter(statusFilter.filter(s => s !== 'cancelled'));
                } else {
                  setStatusFilter([...statusFilter, 'cancelled']);
                }
              }}
            />
          </Box>

          {/* Clear All Filters */}
          {(searchQuery || statusFilter.length > 0 || shiftTypeFilter.length > 0 || showMyScheduleOnly) && (
            <Button
              size="small"
              variant="text"
              color="secondary"
              onClick={() => {
                setSearchQuery('');
                setStatusFilter([]);
                setShiftTypeFilter([]);
                setShowMyScheduleOnly(false);
              }}
            >
              Clear All
            </Button>
          )}
        </Box>
      </Paper>

      {/* Timeline Content */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {error && (
            <Alert severity="error" sx={{ m: 2 }}>
              {error}
            </Alert>
          )}

          {!loading && !error && getFilteredTimelineData().length > 0 && (
            <TableContainer sx={{ pb: 2 }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ 
                      minWidth: 150, 
                      backgroundColor: '#f5f5f5', 
                      fontWeight: 'bold',
                      position: 'sticky',
                      left: 0,
                      zIndex: 100
                    }}>
                      Engineers
                    </TableCell>
                    {dateRange.map((date) => {
                      const isToday = date.toDateString() === new Date().toDateString();
                      
                      return (
                        <TableCell 
                          key={date.toISOString()} 
                          sx={{ 
                            minWidth: viewMode === 'year' ? 80 : 120, 
                            backgroundColor: isToday ? '#e3f2fd' : '#f5f5f5', 
                            fontWeight: 'bold',
                            textAlign: 'center',
                            borderLeft: isToday ? '2px solid #1976d2' : 'none',
                            borderRight: isToday ? '2px solid #1976d2' : 'none'
                          }}
                        >
                          {viewMode === 'year' ? (
                            // Condensed format for year view
                            <Typography 
                              variant="caption" 
                              sx={{ 
                                display: 'block',
                                color: isToday ? '#1976d2' : 'inherit',
                                fontWeight: isToday ? 'bold' : 'normal'
                              }}
                            >
                              {date.toLocaleDateString('en-US', { 
                                month: 'numeric', 
                                day: 'numeric' 
                              })}
                            </Typography>
                          ) : (
                            // Full format for other views
                            <>
                              <Typography 
                                sx={{ 
                                  color: isToday ? '#1976d2' : 'inherit',
                                  fontWeight: isToday ? 'bold' : 'normal'
                                }}
                              >
                                {date.toLocaleDateString('en-US', { 
                                  month: 'short', 
                                  day: 'numeric' 
                                })}
                              </Typography>
                              <br />
                              <Typography 
                                variant="caption" 
                                color={isToday ? '#1976d2' : 'text.secondary'}
                                sx={{ fontWeight: isToday ? 'bold' : 'normal' }}
                              >
                                {date.toLocaleDateString('en-US', { weekday: 'short' })}
                                {isToday && ' (Today)'}
                              </Typography>
                            </>
                          )}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {getFilteredTimelineData().map((engineerData) => (
                    <TableRow key={engineerData.engineer}>
                      <TableCell sx={{ 
                        fontWeight: 'bold', 
                        backgroundColor: '#fafafa',
                        position: 'sticky',
                        left: 0,
                        zIndex: 50
                      }}>
                        {engineerData.engineer}
                      </TableCell>
                      {dateRange.map((date) => {
                        const dayShifts = getShiftsForEngineerAndDate(engineerData.engineer, date);
                        const dayLeaves = getLeavesForEngineerAndDate(engineerData.engineer, date);
                        const groupedShifts = groupShiftsByType(dayShifts);
                        const hasEvents = dayShifts.length > 0 || dayLeaves.length > 0;
                        const isToday = date.toDateString() === new Date().toDateString();
                        
                        return (
                          <TableCell 
                            key={date.toISOString()}
                            sx={{ 
                              p: 0.5,
                              verticalAlign: 'top',
                              backgroundColor: isToday 
                                ? (hasEvents ? '#e3f2fd' : '#f3f9ff')
                                : (hasEvents ? '#fafafa' : 'transparent'),
                              borderLeft: isToday ? '2px solid #1976d2' : 'none',
                              borderRight: isToday ? '2px solid #1976d2' : 'none'
                            }}
                          >
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                              {/* Render shifts */}
                              {Object.entries(groupedShifts).map(([shiftType, shifts]) => {
                                // Create label with count if multiple shifts
                                const count = shifts.length;
                                
                                const label = count > 1 
                                  ? `${formatShiftType(shiftType)} (${count}x)`
                                  : `${formatShiftType(shiftType)}`;
                                
                                return (
                                  <Chip
                                    key={shiftType}
                                    label={label}
                                    size="small"
                                    clickable
                                    onClick={() => handleChipClick(shifts)}
                                    sx={{
                                      backgroundColor: getShiftColor(shiftType),
                                      color: 'white',
                                      fontSize: '0.7rem',
                                      height: 'auto',
                                      cursor: 'pointer',
                                      '&:hover': {
                                        opacity: 0.8,
                                        transform: 'scale(1.02)',
                                      },
                                      '& .MuiChip-label': {
                                        whiteSpace: 'normal',
                                        lineHeight: 1.2,
                                        padding: '2px 4px',
                                        textAlign: 'center'
                                      }
                                    }}
                                  />
                                );
                              })}
                              
                              {/* Render leave requests */}
                              {dayLeaves.map((leave) => {
                                const startDate = new Date(leave.start);
                                const endDate = new Date(leave.end);
                                const isMultiDay = startDate.toDateString() !== endDate.toDateString();
                                
                                let additionalInfo = '';
                                if (isMultiDay) {
                                  // For multi-day leaves, show which day of the leave this is
                                  const daysDiff = Math.ceil((date.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
                                  const totalDays = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1;
                                  additionalInfo = ` - Day ${daysDiff + 1}/${totalDays}`;
                                }
                                
                                const label = `${leave.extendedProps?.leave_type_name || 'Leave'} (${leave.extendedProps?.isRecurring ? 'Recurring' : (leave.extendedProps?.status || 'Unknown')})${additionalInfo}`;
                                
                                return (
                                  <Chip
                                    key={`leave-${leave.id}`}
                                    label={label}
                                    size="small"
                                    clickable
                                    onClick={() => {
                                      // Handle leave click - could show leave details
                                      console.log('Leave clicked:', leave);
                                    }}
                                    sx={{
                                      backgroundColor: leave.backgroundColor || '#90a4ae',
                                      color: 'white',
                                      fontSize: '0.7rem',
                                      height: 'auto',
                                      cursor: 'pointer',
                                      border: '1px solid rgba(255,255,255,0.3)',
                                      '&:hover': {
                                        opacity: 0.8,
                                        transform: 'scale(1.02)',
                                      },
                                      '& .MuiChip-label': {
                                        whiteSpace: 'normal',
                                        lineHeight: 1.2,
                                        padding: '2px 4px',
                                        textAlign: 'center'
                                      }
                                    }}
                                  />
                                );
                              })}
                            </Box>
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {!loading && !error && timelineData.length === 0 && (
            <Box sx={{ textAlign: 'center', p: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No shifts found. Create some shifts using the Orchestrator to see them here.
              </Typography>
            </Box>
          )}

          {!loading && !error && timelineData.length > 0 && getFilteredTimelineData().length === 0 && (
            <Box sx={{ textAlign: 'center', p: 4 }}>
              <Typography variant="body1" color="text.secondary" gutterBottom>
                No shifts match your current filters.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Try adjusting your filters or click "Clear All" to reset.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      {timelineData.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Legend
            </Typography>
            <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
              {/* Shift Types */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ width: 20, height: 20, backgroundColor: '#2196f3', borderRadius: 1 }} />
                <Typography variant="body2">Incidents</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ width: 20, height: 20, backgroundColor: '#ff9800', borderRadius: 1 }} />
                <Typography variant="body2">Incidents-Standby</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ width: 20, height: 20, backgroundColor: '#9c27b0', borderRadius: 1 }} />
                <Typography variant="body2">Waakdienst</Typography>
              </Box>
              
              {/* Leave Request Status */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ width: 20, height: 20, backgroundColor: '#2e7d32', borderRadius: 1 }} />
                <Typography variant="body2">Approved Leave</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ width: 20, height: 20, backgroundColor: '#e65100', borderRadius: 1 }} />
                <Typography variant="body2">Pending Leave</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ width: 20, height: 20, backgroundColor: '#f44336', borderRadius: 1 }} />
                <Typography variant="body2">Rejected Leave</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ width: 20, height: 20, backgroundColor: '#9e9e9e', borderRadius: 1 }} />
                <Typography variant="body2">Cancelled Leave</Typography>
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Shifts show type and time range • Leave requests show type, status, and duration
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Shift Details Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            Shift Details
          </Typography>
          <IconButton onClick={handleCloseDialog} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedShifts.length > 0 && (
            <>
              <Typography variant="subtitle1" gutterBottom>
                {formatShiftType(selectedShifts[0].extendedProps?.shiftType || 'Unknown')} 
                {selectedShifts.length > 1 && ` (${selectedShifts.length} shifts)`}
              </Typography>
              <List>
                {selectedShifts.map((shift, index) => (
                  <React.Fragment key={shift.id || index}>
                    <ListItem sx={{ px: 0 }}>
                      <ListItemText
                        primary={
                          <Box>
                            <Typography variant="body1" fontWeight="bold">
                              {shift.title}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Engineer: {shift.extendedProps?.engineerName || 'Unassigned'}
                            </Typography>
                          </Box>
                        }
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="body2">
                              <strong>Start:</strong> {new Date(shift.start).toLocaleString('en-US', {
                                weekday: 'short',
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </Typography>
                            <Typography variant="body2">
                              <strong>End:</strong> {new Date(shift.end).toLocaleString('en-US', {
                                weekday: 'short',
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </Typography>
                            <Typography variant="body2">
                              <strong>Duration:</strong> {
                                Math.round((new Date(shift.end).getTime() - new Date(shift.start).getTime()) / (1000 * 60 * 60 * 100)) / 100
                              } hours
                            </Typography>
                            {shift.extendedProps?.description && (
                              <Typography variant="body2">
                                <strong>Description:</strong> {shift.extendedProps.description}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < selectedShifts.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TimelinePage;
