import React, { useState, useRef } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import timelinePlugin from '@fullcalendar/timeline';
import resourceTimelinePlugin from '@fullcalendar/resource-timeline';
import resourcePlugin from '@fullcalendar/resource';
import interactionPlugin from '@fullcalendar/interaction';
import {
  Box,
  Paper,
  Typography,
  Toolbar,
  Button,
  ButtonGroup,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Stack,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Badge,
  TextField,
  IconButton,
} from '@mui/material';
import { DateSelectArg, EventDropArg, EventClickArg } from '@fullcalendar/core';
import { 
  Schedule as ScheduleIcon, 
  Person as PersonIcon, 
  AccessTime as TimeIcon,
  SwapHoriz as SwapIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Today as TodayIcon,
  DateRange as DateRangeIcon
} from '@mui/icons-material';

interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  resourceId?: string;
  backgroundColor?: string;
  borderColor?: string;
  extendedProps?: {
    shiftType: 'incident' | 'incidents' | 'incidents_standby' | 'waakdienst' | 'project' | 'change';
    engineerName: string;
    engineerId: string;
    status: 'confirmed' | 'pending' | 'swap_requested';
  };
}

interface CalendarProps {
  events: CalendarEvent[];
  onEventDrop?: (info: EventDropArg) => void;
  onEventClick?: (info: EventClickArg) => void;
  onDateSelect?: (info: DateSelectArg) => void;
}

const shiftTypeColors: Record<string, string> = {
  incident: '#f44336', // Red
  incidents: '#f44336', // Red (alternative naming)
  incidents_standby: '#ff5722', // Deep Orange  
  waakdienst: '#2196f3', // Blue
  project: '#4caf50', // Green
  change: '#ff9800', // Orange
};

const Calendar: React.FC<CalendarProps> = ({
  events,
  onEventDrop,
  onEventClick,
  onDateSelect,
}) => {
  const [currentView, setCurrentView] = useState<string>('dayGridMonth');
  const [filterShiftType, setFilterShiftType] = useState<string>('all');
  const [filterEngineer, setFilterEngineer] = useState<string>('all');
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [eventDialogOpen, setEventDialogOpen] = useState(false);
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const calendarRef = useRef<FullCalendar>(null);

  // Filter events based on current filters
  const filteredEvents = events.filter((event) => {
    if (filterShiftType !== 'all' && event.extendedProps?.shiftType !== filterShiftType) {
      return false;
    }
    if (filterEngineer !== 'all' && event.extendedProps?.engineerId !== filterEngineer) {
      return false;
    }
    return true;
  });

  // Add colors to events based on shift type with safe fallback
  const coloredEvents = filteredEvents.map((event) => {
    const shiftType = event.extendedProps?.shiftType || 'incident';
    const color = shiftTypeColors[shiftType] || shiftTypeColors.incident;
    
    return {
      ...event,
      backgroundColor: event.backgroundColor || color,
      borderColor: event.borderColor || color,
      // Add resourceId for timeline/Gantt views
      resourceId: event.extendedProps?.engineerId,
    };
  });

  const handleViewChange = (view: string) => {
    setCurrentView(view);
    if (calendarRef.current) {
      calendarRef.current.getApi().changeView(view);
    }
  };

  // Navigation functions
  const goToPrevious = () => {
    if (calendarRef.current) {
      calendarRef.current.getApi().prev();
      updateCurrentDate();
    }
  };

  const goToNext = () => {
    if (calendarRef.current) {
      calendarRef.current.getApi().next();
      updateCurrentDate();
    }
  };

  const goToToday = () => {
    if (calendarRef.current) {
      calendarRef.current.getApi().today();
      setCurrentDate(new Date());
    }
  };

  const goToDate = (date: Date) => {
    if (calendarRef.current) {
      calendarRef.current.getApi().gotoDate(date);
      setCurrentDate(date);
    }
  };

  const updateCurrentDate = () => {
    if (calendarRef.current) {
      const calendarApi = calendarRef.current.getApi();
      setCurrentDate(calendarApi.getDate());
    }
  };

  // Format the current date for display
  const formatCurrentPeriod = () => {
    if (currentView === 'dayGridMonth') {
      return currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    } else if (currentView === 'timeGridWeek') {
      // Calculate week start (Monday)
      const weekStart = new Date(currentDate);
      const day = weekStart.getDay();
      const diff = weekStart.getDate() - day + (day === 0 ? -6 : 1);
      weekStart.setDate(diff);
      
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      
      return `${weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
    } else {
      return currentDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    }
  };

  const handleEventDrop = (info: EventDropArg) => {
    if (onEventDrop) {
      onEventDrop(info);
    }
  };

  const handleEventClick = (info: EventClickArg) => {
    // Show detailed event info in dialog
    const eventData = {
      id: info.event.id,
      title: info.event.title,
      start: info.event.start?.toISOString() || '',
      end: info.event.end?.toISOString() || '',
      extendedProps: info.event.extendedProps
    } as CalendarEvent;
    
    setSelectedEvent(eventData);
    setEventDialogOpen(true);
    
    if (onEventClick) {
      onEventClick(info);
    }
  };

  const handleDateSelect = (info: DateSelectArg) => {
    if (onDateSelect) {
      onDateSelect(info);
    }
  };

  // Calculate statistics for better UX
  const shiftStats = filteredEvents.reduce((acc, event) => {
    const shiftType = event.extendedProps?.shiftType || 'unknown';
    acc[shiftType] = (acc[shiftType] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const totalShifts = filteredEvents.length;
  const activeEngineers = new Set(filteredEvents.map(e => e.extendedProps?.engineerId)).size;
  const uniqueEngineers = Array.from(
    new Set(events.map((event) => event.extendedProps?.engineerId).filter(Boolean))
  ).map((engineerId) => {
    const event = events.find((e) => e.extendedProps?.engineerId === engineerId);
    return {
      id: engineerId,
      name: event?.extendedProps?.engineerName || engineerId,
    };
  });

  return (
    <Paper elevation={2} sx={{ p: 2, width: '100%', height: '100%' }}>
      {/* Calendar Controls */}
      <Box sx={{ mb: 2 }}>
        <Toolbar sx={{ px: 0, minHeight: 'auto !important' }}>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h5" component="div">
              Shift Calendar
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {totalShifts} shifts • {activeEngineers} engineers active
            </Typography>
          </Box>

          {/* Current Period Display */}
          <Box sx={{ mx: 2, textAlign: 'center' }}>
            <Typography variant="h6" component="div">
              {formatCurrentPeriod()}
            </Typography>
            <TextField
              type="date"
              size="small"
              value={currentDate.toISOString().split('T')[0]}
              onChange={(e) => {
                const newDate = new Date(e.target.value);
                goToDate(newDate);
              }}
              sx={{ 
                '& .MuiInputBase-input': { 
                  fontSize: '0.875rem',
                  padding: '4px 8px'
                }
              }}
            />
          </Box>
          
          {/* Navigation Controls */}
          <ButtonGroup variant="outlined" sx={{ mr: 2 }}>
            <Tooltip title="Previous">
              <Button onClick={goToPrevious}>
                <ChevronLeftIcon />
              </Button>
            </Tooltip>
            <Tooltip title="Today">
              <Button onClick={goToToday}>
                <TodayIcon />
              </Button>
            </Tooltip>
            <Tooltip title="Next">
              <Button onClick={goToNext}>
                <ChevronRightIcon />
              </Button>
            </Tooltip>
          </ButtonGroup>
          
          {/* View Controls */}
          <ButtonGroup variant="outlined" sx={{ mr: 2 }}>
            <Button
              variant={currentView === 'dayGridMonth' ? 'contained' : 'outlined'}
              onClick={() => handleViewChange('dayGridMonth')}
            >
              Month
            </Button>
            <Button
              variant={currentView === 'timeGridWeek' ? 'contained' : 'outlined'}
              onClick={() => handleViewChange('timeGridWeek')}
            >
              Week
            </Button>
            <Button
              variant={currentView === 'timeGridDay' ? 'contained' : 'outlined'}
              onClick={() => handleViewChange('timeGridDay')}
            >
              Day
            </Button>
            <Button
              variant={currentView === 'timelineWeek' ? 'contained' : 'outlined'}
              onClick={() => handleViewChange('timelineWeek')}
            >
              Timeline
            </Button>
            <Button
              variant={currentView === 'resourceTimelineWeek' ? 'contained' : 'outlined'}
              onClick={() => handleViewChange('resourceTimelineWeek')}
            >
              Gantt
            </Button>
          </ButtonGroup>
        </Toolbar>

        {/* Filters */}
        <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Shift Type</InputLabel>
            <Select
              value={filterShiftType}
              label="Shift Type"
              onChange={(e) => setFilterShiftType(e.target.value)}
            >
              <MenuItem value="all">All Types</MenuItem>
              <MenuItem value="incident">Incidents (INC)</MenuItem>
              <MenuItem value="incidents">Incidents (INC)</MenuItem>
              <MenuItem value="incidents_standby">Incidents-Standby (SBY)</MenuItem>
              <MenuItem value="waakdienst">Waakdienst (WD)</MenuItem>
              <MenuItem value="project">Projects (PRJ)</MenuItem>
              <MenuItem value="change">Changes (CHG)</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Engineer</InputLabel>
            <Select
              value={filterEngineer}
              label="Engineer"
              onChange={(e) => setFilterEngineer(e.target.value)}
            >
              <MenuItem value="all">All Engineers</MenuItem>
              {uniqueEngineers.map((engineer) => (
                <MenuItem key={engineer.id} value={engineer.id}>
                  {engineer.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Legend with counts */}
          <Stack direction="row" spacing={1} sx={{ ml: 'auto' }}>
            <Badge badgeContent={shiftStats.incident || shiftStats.incidents || 0} color="error">
              <Chip
                label="INC - Incidents"
                size="small"
                sx={{ backgroundColor: shiftTypeColors.incident, color: 'white' }}
              />
            </Badge>
            <Badge badgeContent={shiftStats.incidents_standby || 0} color="warning">
              <Chip
                label="SBY - Standby"
                size="small"
                sx={{ backgroundColor: shiftTypeColors.incidents_standby, color: 'white' }}
              />
            </Badge>
            <Badge badgeContent={shiftStats.waakdienst || 0} color="primary">
              <Chip
                label="WD - Waakdienst"
                size="small"
                sx={{ backgroundColor: shiftTypeColors.waakdienst, color: 'white' }}
              />
            </Badge>
            <Badge badgeContent={shiftStats.project || 0} color="success">
              <Chip
                label="PRJ - Projects"
                size="small"
                sx={{ backgroundColor: shiftTypeColors.project, color: 'white' }}
              />
            </Badge>
            <Badge badgeContent={shiftStats.change || 0} color="warning">
              <Chip
                label="CHG - Changes"
                size="small"
                sx={{ backgroundColor: shiftTypeColors.change, color: 'white' }}
              />
            </Badge>
          </Stack>
        </Stack>
      </Box>

      {/* Calendar */}
      <Box 
        sx={{ 
          height: 'calc(100vh - 300px)', 
          minHeight: '500px', 
          width: '100%',
          // Custom styles for compact events
          '& .fc-event': {
            minHeight: '20px !important',
            padding: '1px 2px !important',
            marginBottom: '1px !important',
            borderRadius: '3px !important',
            fontSize: '11px !important'
          },
          '& .fc-event-title': {
            fontSize: '11px !important',
            fontWeight: 500
          },
          '& .fc-daygrid-event': {
            marginBottom: '1px !important',
            minHeight: '18px !important'
          },
          '& .fc-event-main': {
            padding: '1px 3px !important'
          },
          '& .fc-daygrid-day-events': {
            marginBottom: '2px !important'
          }
        }}
      >
        <FullCalendar
          ref={calendarRef}
          plugins={[dayGridPlugin, timeGridPlugin, timelinePlugin, resourceTimelinePlugin, resourcePlugin, interactionPlugin]}
          initialView={currentView}
          headerToolbar={false} // We use custom toolbar
          height="100%"
          firstDay={1} // Start week on Monday (0=Sunday, 1=Monday, etc.)
          
          // 24-hour time format
          slotLabelFormat={{
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
          }}
          eventTimeFormat={{
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
          }}
          
          // DD/MM/YYYY date format - view specific
          views={{
            dayGridMonth: {
              titleFormat: { year: 'numeric', month: 'long' },
              dayHeaderFormat: { weekday: 'narrow' } // Just show single letters: M T W T F S S
            },
            timeGridWeek: {
              titleFormat: { year: 'numeric', month: 'short', day: '2-digit' },
              dayHeaderFormat: { weekday: 'short', day: 'numeric', month: 'numeric' }
            },
            timeGridDay: {
              titleFormat: { year: 'numeric', month: 'long', day: '2-digit' }
            },
            timelineWeek: {
              type: 'timeline',
              duration: { weeks: 1 },
              slotDuration: { days: 1 },
              titleFormat: { year: 'numeric', month: 'short', day: '2-digit' }
            },
            resourceTimelineWeek: {
              type: 'resourceTimeline',
              duration: { weeks: 1 },
              slotDuration: { days: 1 },
              resourceAreaHeaderContent: 'Engineers',
              titleFormat: { year: 'numeric', month: 'short', day: '2-digit' }
            }
          }}
          
          // Resources configuration for Gantt/Timeline views
          resources={uniqueEngineers.map(engineer => ({
            id: engineer.id,
            title: engineer.name,
            eventColor: shiftTypeColors.incident // Default color
          }))}
          
          events={coloredEvents}
          
          // Interaction
          editable={true}
          droppable={true}
          selectable={true}
          selectMirror={true}
          
          // Event handlers
          eventDrop={handleEventDrop}
          eventClick={handleEventClick}
          select={handleDateSelect}
          
          // Styling
          eventDisplay="block"
          dayMaxEvents={6} // Increased to show more events
          moreLinkClick="popover" // Show overflow events in popover
          
          // Custom styling for more compact events
          eventClassNames={() => {
            return ['compact-event']; // Add custom CSS class
          }}
          
          // Make events more compact
          dayMaxEventRows={4} // Limit rows in month view
          
          // Business hours (for incidents: Mon-Fri 8-17)
          businessHours={{
            daysOfWeek: [1, 2, 3, 4, 5], // Monday - Friday
            startTime: '08:00',
            endTime: '17:00',
          }}
          
          // Custom event content - much more compact
          eventContent={(eventInfo) => {
            const { event } = eventInfo;
            const props = event.extendedProps;
            
            // Create a compact single-line format with flexible mapping
            const shiftTypeMap: Record<string, string> = {
              incident: 'INC',
              incidents: 'INC', // Alternative backend naming
              incidents_standby: 'SBY',
              waakdienst: 'WD',
              project: 'PRJ',
              change: 'CHG'
            };
            const shiftTypeAbbrev = shiftTypeMap[props.shiftType] || props.shiftType?.substring(0, 3).toUpperCase();
            
            // Get first name only for space efficiency
            const firstName = props.engineerName?.split(' ')[0] || 'Unknown';
            
            // Get start and end times for tooltip (safely handle potential null dates)
            const startTime = eventInfo.event.start ? eventInfo.event.start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
            const endTime = eventInfo.event.end ? eventInfo.event.end.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
            const dateString = eventInfo.event.start ? eventInfo.event.start.toLocaleDateString() : '';
            const timeString = `${dateString} ${startTime}${endTime ? ' - ' + endTime : ''}`;
            
            return (
              <Tooltip 
                title={`${shiftTypeAbbrev} - ${props.engineerName} | ${timeString}`}
                arrow
                placement="top"
              >
                <Box 
                  sx={{ 
                    p: '2px 4px',
                    overflow: 'hidden',
                    height: '18px',
                    lineHeight: '14px',
                    fontSize: '11px',
                    fontWeight: 500,
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                    cursor: 'pointer',
                    borderRadius: '3px',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      transform: 'scale(1.02)',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                      zIndex: 1000
                    },
                    '& .shift-type': {
                      fontWeight: 'bold'
                    },
                    '& .swap-badge': {
                      backgroundColor: 'rgba(255,193,7,0.9)', 
                      padding: '0 2px', 
                      borderRadius: '2px',
                      fontSize: '9px',
                      color: '#000',
                      fontWeight: 'bold'
                    }
                  }}
                >
                  <span className="shift-type">{shiftTypeAbbrev}</span>
                  <span>•</span>
                  <span>{firstName}</span>
                  {props.status === 'swap_requested' && (
                    <span className="swap-badge">SWAP</span>
                  )}
                </Box>
              </Tooltip>
            );
          }}
        />
      </Box>

      {/* Event Details Dialog */}
      <Dialog 
        open={eventDialogOpen} 
        onClose={() => setEventDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ScheduleIcon />
          Shift Details
        </DialogTitle>
        <DialogContent>
          {selectedEvent && (
            <List>
              <ListItem>
                <ListItemIcon>
                  <PersonIcon />
                </ListItemIcon>
                <ListItemText 
                  primary="Engineer" 
                  secondary={selectedEvent.extendedProps?.engineerName || 'Unknown'}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <ScheduleIcon />
                </ListItemIcon>
                <ListItemText 
                  primary="Shift Type" 
                  secondary={
                    <Chip 
                      label={selectedEvent.extendedProps?.shiftType?.toUpperCase() || 'UNKNOWN'}
                      size="small"
                      sx={{ 
                        backgroundColor: shiftTypeColors[selectedEvent.extendedProps?.shiftType || 'incident'],
                        color: 'white'
                      }}
                    />
                  }
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <TimeIcon />
                </ListItemIcon>
                <ListItemText 
                  primary="Time Period" 
                  secondary={`${new Date(selectedEvent.start).toLocaleString()} - ${new Date(selectedEvent.end).toLocaleString()}`}
                />
              </ListItem>
              {selectedEvent.extendedProps?.status === 'swap_requested' && (
                <ListItem>
                  <ListItemIcon>
                    <SwapIcon />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Status" 
                    secondary={
                      <Chip 
                        label="SWAP REQUESTED"
                        size="small"
                        color="warning"
                        icon={<SwapIcon />}
                      />
                    }
                  />
                </ListItem>
              )}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEventDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default Calendar;
