import React, { useState, useEffect } from 'react';
import { Box, Alert, CircularProgress } from '@mui/material';
import Calendar from '../components/calendar/Calendar';
import { EventDropArg, EventClickArg, DateSelectArg } from '@fullcalendar/core';
import { CalendarEvent } from '../types/calendar';
import axios from 'axios';

const CalendarPage: React.FC = () => {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch shifts from the API
  // Fetch shifts from the API
  useEffect(() => {
    const fetchShifts = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Call the shifts API directly (not through the DRF API router)
        const response = await axios.get('http://localhost:8000/shifts/api/shifts/');
        const data = response.data as { events: CalendarEvent[] };
        setEvents(data.events);
      } catch (err) {
        console.error('Failed to fetch shifts:', err);
        setError('Failed to load shifts. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchShifts();
  }, []);

  const handleEventDrop = (info: EventDropArg) => {
    // Handle event drop - this would trigger a swap request
    const { event } = info;
    
    console.log('Event dropped:', {
      eventId: event.id,
      newStart: event.start,
      newEnd: event.end,
      oldStart: info.oldEvent.start,
      oldEnd: info.oldEvent.end,
    });

    // Simulate API call to create swap request
    setLoading(true);
    setTimeout(() => {
      // Update event status to indicate swap request
      setEvents(prevEvents =>
        prevEvents.map(e => {
          if (e.id === event.id && e.extendedProps) {
            return {
              ...e,
              start: event.start?.toISOString() || e.start,
              end: event.end?.toISOString() || e.end,
              extendedProps: {
                ...e.extendedProps,
                status: 'swap_requested',
              },
            };
          }
          return e;
        })
      );
      setLoading(false);
      
      // Show success message
      setError(null);
      console.log('Swap request created successfully');
    }, 1000);
  };

  const handleEventClick = (info: EventClickArg) => {
    // Handle event click - show event details
    const { event } = info;
    console.log('Event clicked:', event.extendedProps);
    
    // TODO: Open event details modal
    alert(`Event Details:
    Engineer: ${event.extendedProps.engineerName}
    Shift Type: ${event.extendedProps.shiftType}
    Status: ${event.extendedProps.status}
    Start: ${event.start}
    End: ${event.end}`);
  };

  const handleDateSelect = (info: DateSelectArg) => {
    // Handle date selection - create new shift
    console.log('Date selected:', {
      start: info.start,
      end: info.end,
    });
    
    // TODO: Open create shift modal
    const newShift = confirm(`Create new shift for ${info.start.toLocaleDateString()}?`);
    if (newShift) {
      console.log('Creating new shift...');
      // TODO: Implement shift creation
    }
  };

  return (
    <Box sx={{ width: '100%', height: '100%', py: 4, px: 3 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
          <CircularProgress />
        </Box>
      )}
      
      <Calendar
        events={events}
        onEventDrop={handleEventDrop}
        onEventClick={handleEventClick}
        onDateSelect={handleDateSelect}
      />
    </Box>
  );
};

export default CalendarPage;
