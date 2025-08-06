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
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  ChevronLeft,
  ChevronRight,
  Today,
  Close,
} from '@mui/icons-material';
import axios from 'axios';
import { CalendarEvent } from '../types/calendar';

interface TimelineData {
  engineer: string;
  shifts: CalendarEvent[];
}

const TimelinePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'week' | 'month' | 'quarter' | 'year'>('month');
  const [timelineData, setTimelineData] = useState<TimelineData[]>([]);
  const [dateRange, setDateRange] = useState<Date[]>([]);
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [allShiftsData, setAllShiftsData] = useState<CalendarEvent[]>([]);
  const [selectedShifts, setSelectedShifts] = useState<CalendarEvent[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Fetch shifts from API
  const fetchShifts = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Call the shifts API directly (same as CalendarPage)
      const response = await axios.get('http://localhost:8000/shifts/api/shifts/');
      const data = response.data as { events: CalendarEvent[] };
      setAllShiftsData(data.events);
      
      // Use today's date for initial processing
      const today = new Date();
      processTimelineData(data.events, today);
    } catch (err) {
      setError('Failed to load shifts');
      console.error('Error loading shifts:', err);
    } finally {
      setLoading(false);
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

  // Process shifts into timeline format
  const processTimelineData = (shiftsData: CalendarEvent[], baseDate?: Date) => {
    // Group shifts by engineer
    const engineerGroups: { [key: string]: CalendarEvent[] } = {};
    
    shiftsData.forEach((shift) => {
      const engineerName = shift.extendedProps?.engineerName || 'Unassigned';
      if (!engineerGroups[engineerName]) {
        engineerGroups[engineerName] = [];
      }
      engineerGroups[engineerName].push(shift);
    });

    // Convert to timeline data
    const timeline: TimelineData[] = Object.entries(engineerGroups)
      .map(([engineer, shifts]) => ({ engineer, shifts }))
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
        return `${weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
      case 'month':
        const monthEnd = new Date(currentDate);
        monthEnd.setDate(monthEnd.getDate() + 30);
        return `${currentDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${monthEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
      case 'quarter':
        const quarterEnd = new Date(currentDate);
        quarterEnd.setDate(quarterEnd.getDate() + 90);
        return `${currentDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${quarterEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
      case 'year':
        const yearEnd = new Date(currentDate);
        yearEnd.setDate(yearEnd.getDate() + 365);
        return `${currentDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} - ${yearEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
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

  // Load shifts on component mount
  useEffect(() => {
    fetchShifts();
    // Set current date to today when component first loads
    const today = new Date();
    setCurrentDate(today);
  }, []);

  // Regenerate timeline when view mode or current date changes
  useEffect(() => {
    if (allShiftsData.length > 0) {
      processTimelineData(allShiftsData);
    }
  }, [viewMode, currentDate, allShiftsData]);

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
              {timelineData.length} engineers, {timelineData.reduce((sum, td) => sum + td.shifts.length, 0)} shifts
            </Typography>
          </Box>
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

          {!loading && !error && timelineData.length > 0 && (
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
                  {timelineData.map((engineerData) => (
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
                        const groupedShifts = groupShiftsByType(dayShifts);
                        const isToday = date.toDateString() === new Date().toDateString();
                        
                        return (
                          <TableCell 
                            key={date.toISOString()}
                            sx={{ 
                              p: 0.5,
                              verticalAlign: 'top',
                              backgroundColor: isToday 
                                ? (dayShifts.length > 0 ? '#e3f2fd' : '#f3f9ff')
                                : (dayShifts.length > 0 ? '#fafafa' : 'transparent'),
                              borderLeft: isToday ? '2px solid #1976d2' : 'none',
                              borderRight: isToday ? '2px solid #1976d2' : 'none'
                            }}
                          >
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                              {Object.entries(groupedShifts).map(([shiftType, shifts]) => {
                                // Get the earliest start and latest end time for this shift type
                                const startTimes = shifts.map(s => new Date(s.start));
                                const endTimes = shifts.map(s => new Date(s.end));
                                const earliestStart = new Date(Math.min(...startTimes.map(d => d.getTime())));
                                const latestEnd = new Date(Math.max(...endTimes.map(d => d.getTime())));
                                
                                // Create label with count if multiple shifts
                                const count = shifts.length;
                                const timeRange = `${earliestStart.toLocaleTimeString('en-US', { 
                                  hour: '2-digit', 
                                  minute: '2-digit',
                                  hour12: false 
                                })}-${latestEnd.toLocaleTimeString('en-US', { 
                                  hour: '2-digit', 
                                  minute: '2-digit',
                                  hour12: false 
                                })}`;
                                
                                const label = count > 1 
                                  ? `${formatShiftType(shiftType)} (${count}x) ${timeRange}`
                                  : `${formatShiftType(shiftType)} ${timeRange}`;
                                
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
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Each chip shows shift type and time range
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
