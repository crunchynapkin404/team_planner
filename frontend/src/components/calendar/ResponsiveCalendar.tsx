import React from 'react';
import { useTheme, useMediaQuery } from '@mui/material';
import Calendar from './Calendar';
import MobileCalendar from './MobileCalendar';
import { EventDropArg, EventClickArg, DateSelectArg } from '@fullcalendar/core';
import { CalendarEvent } from '../../types/calendar';

interface ResponsiveCalendarProps {
  events: CalendarEvent[];
  onEventDrop?: (info: EventDropArg) => void;
  onEventClick?: (info: EventClickArg) => void;
  onDateSelect?: (info: DateSelectArg) => void;
}

/**
 * ResponsiveCalendar - Automatically switches between desktop and mobile calendar views
 * 
 * Features:
 * - Desktop (md+): Full-featured FullCalendar with multiple views
 * - Mobile (sm-): Touch-optimized calendar with swipe gestures
 * - Automatic view switching based on screen size
 * - Consistent event data structure across both views
 */
const ResponsiveCalendar: React.FC<ResponsiveCalendarProps> = ({
  events,
  onEventDrop,
  onEventClick,
  onDateSelect,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Convert DateSelectArg to simple Date for mobile calendar
  const handleMobileDateSelect = (date: Date) => {
    if (onDateSelect) {
      // Create a DateSelectArg-like object for compatibility
      const dateSelectInfo = {
        start: date,
        end: date,
        startStr: date.toISOString(),
        endStr: date.toISOString(),
        allDay: true,
        view: {
          type: 'dayGridMonth',
        },
      } as unknown as DateSelectArg;
      
      onDateSelect(dateSelectInfo);
    }
  };

  // Convert simple event click to EventClickArg for mobile calendar
  const handleMobileEventClick = (event: CalendarEvent) => {
    if (onEventClick) {
      // Create an EventClickArg-like object for compatibility
      const eventClickInfo = {
        event: {
          id: event.id,
          title: event.title,
          start: new Date(event.start),
          end: new Date(event.end),
          extendedProps: event.extendedProps,
        },
      } as unknown as EventClickArg;
      
      onEventClick(eventClickInfo);
    }
  };

  if (isMobile) {
    return (
      <MobileCalendar
        events={events}
        onEventClick={handleMobileEventClick}
        onDateSelect={handleMobileDateSelect}
      />
    );
  }

  return (
    <Calendar
      events={events}
      onEventDrop={onEventDrop}
      onEventClick={onEventClick}
      onDateSelect={onDateSelect}
    />
  );
};

export default ResponsiveCalendar;
