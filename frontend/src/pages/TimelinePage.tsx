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
} from '@mui/material';
import axios from 'axios';
import { CalendarEvent } from '../types/calendar';

interface TimelineData {
  engineer: string;
  shifts: CalendarEvent[];
}

interface TimeSlot {
  date: string;
  shifts: CalendarEvent[];
}

const TimelinePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'day' | 'week' | 'month'>('week');
  const [timelineData, setTimelineData] = useState<TimelineData[]>([]);
  const [dateRange, setDateRange] = useState<Date[]>([]);

  // Fetch shifts from API
  const fetchShifts = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Call the shifts API directly (same as CalendarPage)
      const response = await axios.get('http://localhost:8000/shifts/api/shifts/');
      const data = response.data as { events: CalendarEvent[] };
      processTimelineData(data.events);
    } catch (err) {
      setError('Failed to load shifts');
      console.error('Error loading shifts:', err);
    } finally {
      setLoading(false);
    }
  };

  // Process shifts into timeline format
  const processTimelineData = (shiftsData: CalendarEvent[]) => {
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

    // Generate date range based on shifts
    if (shiftsData.length > 0) {
      const allDates = shiftsData.flatMap(shift => [
        new Date(shift.start),
        new Date(shift.end)
      ]);
      const minDate = new Date(Math.min(...allDates.map(d => d.getTime())));
      const maxDate = new Date(Math.max(...allDates.map(d => d.getTime())));
      
      // Generate date range
      const dates: Date[] = [];
      const current = new Date(minDate);
      current.setHours(0, 0, 0, 0);
      
      while (current <= maxDate) {
        dates.push(new Date(current));
        current.setDate(current.getDate() + 1);
      }
      
      setDateRange(dates);
    }
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
    setViewMode(event.target.value as 'day' | 'week' | 'month');
  };

  // Load shifts on component mount
  useEffect(() => {
    fetchShifts();
  }, []);

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
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>View Mode</InputLabel>
            <Select
              value={viewMode}
              label="View Mode"
              onChange={handleViewModeChange}
            >
              <MenuItem value="day">Day</MenuItem>
              <MenuItem value="week">Week</MenuItem>
              <MenuItem value="month">Month</MenuItem>
            </Select>
          </FormControl>
          
          <Typography variant="body2" color="text.secondary">
            {timelineData.length} engineers, {timelineData.reduce((sum, td) => sum + td.shifts.length, 0)} shifts
          </Typography>
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
            <TableContainer>
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
                    {dateRange.map((date) => (
                      <TableCell 
                        key={date.toISOString()} 
                        sx={{ 
                          minWidth: 120, 
                          backgroundColor: '#f5f5f5', 
                          fontWeight: 'bold',
                          textAlign: 'center'
                        }}
                      >
                        {date.toLocaleDateString('en-US', { 
                          month: 'short', 
                          day: 'numeric' 
                        })}
                        <br />
                        <Typography variant="caption" color="text.secondary">
                          {date.toLocaleDateString('en-US', { weekday: 'short' })}
                        </Typography>
                      </TableCell>
                    ))}
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
                        
                        return (
                          <TableCell 
                            key={date.toISOString()}
                            sx={{ 
                              p: 0.5,
                              verticalAlign: 'top',
                              backgroundColor: dayShifts.length > 0 ? '#fafafa' : 'transparent'
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
                                    sx={{
                                      backgroundColor: getShiftColor(shiftType),
                                      color: 'white',
                                      fontSize: '0.7rem',
                                      height: 'auto',
                                      '& .MuiChip-label': {
                                        whiteSpace: 'normal',
                                        lineHeight: 1.2,
                                        padding: '2px 4px'
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
    </Box>
  );
};

export default TimelinePage;
