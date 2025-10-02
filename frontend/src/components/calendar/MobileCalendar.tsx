import React, { useState, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Drawer,
  Chip,
  Button,
  Stack,
  Card,
  CardContent,
  CardActions,
  Divider,
  useTheme,
  useMediaQuery,
  SwipeableDrawer,
  Fab,
  Badge,
  Avatar,
} from '@mui/material';
import {
  ChevronLeft,
  ChevronRight,
  Today,
  Event as EventIcon,
  Person as PersonIcon,
  AccessTime,
  Schedule,
  SwapHoriz,
  Close,
  FilterList,
  CalendarMonth,
} from '@mui/icons-material';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, isToday, addMonths, subMonths, startOfWeek, endOfWeek } from 'date-fns';
import { CalendarEvent } from '../../types/calendar';

interface MobileCalendarProps {
  events: CalendarEvent[];
  onEventClick?: (event: CalendarEvent) => void;
  onDateSelect?: (date: Date) => void;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
}

const shiftTypeColors: Record<string, string> = {
  incident: '#f44336',
  incidents: '#f44336',
  incidents_standby: '#ff5722',
  waakdienst: '#2196f3',
  project: '#4caf50',
  change: '#ff9800',
};

const MobileCalendar: React.FC<MobileCalendarProps> = ({
  events,
  onEventClick,
  onDateSelect,
  onSwipeLeft,
  onSwipeRight,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  
  // Touch/swipe detection
  const touchStartX = useRef<number>(0);
  const touchEndX = useRef<number>(0);
  const minSwipeDistance = 50;

  // Get calendar days
  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const calendarStart = startOfWeek(monthStart, { weekStartsOn: 1 });
  const calendarEnd = endOfWeek(monthEnd, { weekStartsOn: 1 });
  const calendarDays = eachDayOfInterval({ start: calendarStart, end: calendarEnd });

  // Get events for a specific date
  const getEventsForDate = (date: Date): CalendarEvent[] => {
    return events.filter(event => {
      const eventStart = new Date(event.start);
      return isSameDay(eventStart, date);
    });
  };

  // Get events for selected date
  const selectedDateEvents = selectedDate ? getEventsForDate(selectedDate) : [];

  // Navigation
  const goToPreviousMonth = () => {
    setCurrentDate(subMonths(currentDate, 1));
    onSwipeRight?.();
  };

  const goToNextMonth = () => {
    setCurrentDate(addMonths(currentDate, 1));
    onSwipeLeft?.();
  };

  const goToToday = () => {
    setCurrentDate(new Date());
    setSelectedDate(new Date());
  };

  // Touch handlers for swipe gestures
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    touchEndX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = () => {
    if (touchStartX.current - touchEndX.current > minSwipeDistance) {
      // Swipe left - next month
      goToNextMonth();
    }
    if (touchEndX.current - touchStartX.current > minSwipeDistance) {
      // Swipe right - previous month
      goToPreviousMonth();
    }
  };

  // Handle date click
  const handleDateClick = (date: Date) => {
    setSelectedDate(date);
    const dateEvents = getEventsForDate(date);
    if (dateEvents.length > 0) {
      setDetailDrawerOpen(true);
    }
    onDateSelect?.(date);
  };

  // Handle event click
  const handleEventClick = (event: CalendarEvent) => {
    onEventClick?.(event);
  };

  // Get event color
  const getEventColor = (event: CalendarEvent): string => {
    if (event.extendedProps?.eventType === 'leave') {
      return event.extendedProps.leave_type_color || '#9c27b0';
    }
    const shiftType = event.extendedProps?.shiftType || 'incident';
    return shiftTypeColors[shiftType] || shiftTypeColors.incident;
  };

  // Render day cell
  const renderDayCell = (date: Date) => {
    const dayEvents = getEventsForDate(date);
    const isCurrentMonth = isSameMonth(date, currentDate);
    const isSelected = selectedDate && isSameDay(date, selectedDate);
    const isTodayDate = isToday(date);

    return (
      <Box
        key={date.toISOString()}
        onClick={() => handleDateClick(date)}
        sx={{
          aspectRatio: '1',
          border: '1px solid',
          borderColor: 'divider',
          p: isMobile ? 0.5 : 1,
          cursor: 'pointer',
          position: 'relative',
          backgroundColor: isSelected ? 'action.selected' : 'background.paper',
          opacity: isCurrentMonth ? 1 : 0.4,
          '&:hover': {
            backgroundColor: 'action.hover',
          },
          '&:active': {
            backgroundColor: 'action.selected',
          },
        }}
      >
        {/* Day number */}
        <Typography
          variant={isMobile ? 'caption' : 'body2'}
          sx={{
            fontWeight: isTodayDate ? 'bold' : 'normal',
            color: isTodayDate ? 'primary.main' : 'text.primary',
          }}
        >
          {format(date, 'd')}
        </Typography>

        {/* Event indicators */}
        {dayEvents.length > 0 && (
          <Box
            sx={{
              position: 'absolute',
              bottom: isMobile ? 2 : 4,
              left: '50%',
              transform: 'translateX(-50%)',
              display: 'flex',
              gap: 0.25,
              flexWrap: 'wrap',
              justifyContent: 'center',
              maxWidth: '90%',
            }}
          >
            {dayEvents.slice(0, isMobile ? 2 : 3).map((event, idx) => (
              <Box
                key={idx}
                sx={{
                  width: isMobile ? 4 : 6,
                  height: isMobile ? 4 : 6,
                  borderRadius: '50%',
                  backgroundColor: getEventColor(event),
                }}
              />
            ))}
            {dayEvents.length > (isMobile ? 2 : 3) && (
              <Typography
                variant="caption"
                sx={{
                  fontSize: isMobile ? '0.6rem' : '0.7rem',
                  color: 'text.secondary',
                }}
              >
                +{dayEvents.length - (isMobile ? 2 : 3)}
              </Typography>
            )}
          </Box>
        )}
      </Box>
    );
  };

  // Render event detail card
  const renderEventDetail = (event: CalendarEvent) => {
    const isLeave = event.extendedProps?.eventType === 'leave';
    const color = getEventColor(event);

    return (
      <Card key={event.id} sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" mb={1}>
            <Avatar sx={{ bgcolor: color, width: 32, height: 32 }}>
              {isLeave ? <EventIcon fontSize="small" /> : <Schedule fontSize="small" />}
            </Avatar>
            <Box flex={1}>
              <Typography variant="subtitle1" fontWeight="bold">
                {event.title}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {event.extendedProps?.engineerName}
              </Typography>
            </Box>
            <Chip
              label={event.extendedProps?.status || 'confirmed'}
              size="small"
              color={event.extendedProps?.status === 'confirmed' ? 'success' : 'default'}
            />
          </Stack>

          <Divider sx={{ my: 1 }} />

          <Stack spacing={1}>
            <Stack direction="row" spacing={1} alignItems="center">
              <AccessTime fontSize="small" color="action" />
              <Typography variant="body2">
                {format(new Date(event.start), 'HH:mm')} - {format(new Date(event.end), 'HH:mm')}
              </Typography>
            </Stack>

            {event.extendedProps?.teamName && (
              <Stack direction="row" spacing={1} alignItems="center">
                <PersonIcon fontSize="small" color="action" />
                <Typography variant="body2">
                  Team: {event.extendedProps.teamName}
                </Typography>
              </Stack>
            )}

            {event.extendedProps?.description && (
              <Typography variant="body2" color="text.secondary">
                {event.extendedProps.description}
              </Typography>
            )}

            {isLeave && event.extendedProps?.days_requested && (
              <Typography variant="body2" color="text.secondary">
                Duration: {event.extendedProps.days_requested} days
              </Typography>
            )}
          </Stack>
        </CardContent>

        <CardActions>
          <Button size="small" onClick={() => handleEventClick(event)}>
            View Details
          </Button>
          {event.extendedProps?.status === 'confirmed' && (
            <Button size="small" color="secondary" startIcon={<SwapHoriz />}>
              Request Swap
            </Button>
          )}
        </CardActions>
      </Card>
    );
  };

  return (
    <Box sx={{ width: '100%', height: '100%' }}>
      {/* Header */}
      <Paper
        elevation={2}
        sx={{
          p: isMobile ? 1 : 2,
          mb: 2,
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <IconButton onClick={goToPreviousMonth} size={isMobile ? 'small' : 'medium'}>
            <ChevronLeft />
          </IconButton>

          <Box flex={1} textAlign="center">
            <Typography variant={isMobile ? 'h6' : 'h5'} fontWeight="bold">
              {format(currentDate, 'MMMM yyyy')}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {events.length} events this month
            </Typography>
          </Box>

          <IconButton onClick={goToNextMonth} size={isMobile ? 'small' : 'medium'}>
            <ChevronRight />
          </IconButton>
        </Stack>

        {/* Week day headers */}
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            gap: 0,
            mt: 2,
          }}
        >
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => (
            <Typography
              key={day}
              variant="caption"
              align="center"
              color="text.secondary"
              fontWeight="bold"
            >
              {isMobile ? day.charAt(0) : day}
            </Typography>
          ))}
        </Box>
      </Paper>

      {/* Calendar Grid */}
      <Paper
        elevation={1}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        sx={{
          overflow: 'hidden',
          touchAction: 'pan-y',
        }}
      >
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            gap: 0,
          }}
        >
          {calendarDays.map((date) => renderDayCell(date))}
        </Box>
      </Paper>

      {/* Floating Action Buttons */}
      <Box
        sx={{
          position: 'fixed',
          bottom: isMobile ? 16 : 24,
          right: isMobile ? 16 : 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
          zIndex: 1000,
        }}
      >
        <Fab
          color="primary"
          size={isMobile ? 'medium' : 'large'}
          onClick={goToToday}
        >
          <Today />
        </Fab>
        <Badge badgeContent={events.length} color="secondary" max={99}>
          <Fab
            color="default"
            size={isMobile ? 'small' : 'medium'}
            onClick={() => setFilterDrawerOpen(true)}
          >
            <FilterList />
          </Fab>
        </Badge>
      </Box>

      {/* Event Details Drawer */}
      <SwipeableDrawer
        anchor="bottom"
        open={detailDrawerOpen}
        onClose={() => setDetailDrawerOpen(false)}
        onOpen={() => setDetailDrawerOpen(true)}
        disableSwipeToOpen={false}
        sx={{
          '& .MuiDrawer-paper': {
            maxHeight: '70vh',
            borderTopLeftRadius: 16,
            borderTopRightRadius: 16,
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          {/* Drawer handle */}
          <Box
            sx={{
              width: 40,
              height: 4,
              backgroundColor: 'divider',
              borderRadius: 2,
              mx: 'auto',
              mb: 2,
            }}
          />

          {/* Header */}
          <Stack direction="row" alignItems="center" justifyContent="space-between" mb={2}>
            <Typography variant="h6">
              {selectedDate && format(selectedDate, 'EEEE, MMMM d, yyyy')}
            </Typography>
            <IconButton onClick={() => setDetailDrawerOpen(false)} size="small">
              <Close />
            </IconButton>
          </Stack>

          {/* Events list */}
          {selectedDateEvents.length > 0 ? (
            <Box sx={{ maxHeight: '50vh', overflowY: 'auto' }}>
              {selectedDateEvents.map((event) => renderEventDetail(event))}
            </Box>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <CalendarMonth sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
              <Typography color="text.secondary">
                No events scheduled for this day
              </Typography>
            </Box>
          )}
        </Box>
      </SwipeableDrawer>

      {/* Filter Drawer (placeholder for future implementation) */}
      <Drawer
        anchor="right"
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
      >
        <Box sx={{ width: 280, p: 2 }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" mb={2}>
            <Typography variant="h6">Filters</Typography>
            <IconButton onClick={() => setFilterDrawerOpen(false)} size="small">
              <Close />
            </IconButton>
          </Stack>
          <Typography variant="body2" color="text.secondary">
            Filter options coming soon...
          </Typography>
        </Box>
      </Drawer>
    </Box>
  );
};

export default MobileCalendar;
