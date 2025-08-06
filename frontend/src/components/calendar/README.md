# Calendar Component

## Overview
The Calendar component provides a comprehensive scheduling interface built with FullCalendar.js and Material-UI. It supports multiple views, drag-and-drop functionality, and color-coded shift types.

## Features

### 📅 Multiple Calendar Views
- **Month View** - Traditional monthly calendar grid
- **Week View** - Detailed weekly schedule  
- **Day View** - Hourly day schedule

### 🎨 Visual Features
- **Color Coding** - Different colors for each shift type:
  - 🔴 Incidents (Red)
  - 🔵 Waakdienst (Blue) 
  - 🟢 Projects (Green)
  - 🟠 Changes (Orange)
- **Status Indicators** - Visual badges for swap requests
- **Engineer Names** - Clear identification on shift blocks

### 🖱️ Interactive Features
- **Drag & Drop** - Move shifts between dates (triggers swap requests)
- **Click Events** - View shift details
- **Date Selection** - Create new shifts
- **Filtering** - Filter by shift type and engineer

### 🔧 Business Logic
- **Business Hours** - Highlights incident hours (Mon-Fri 8:00-17:00)
- **Conflict Prevention** - Visual feedback for overlapping shifts
- **Real-time Updates** - Live changes across users (planned)

## Usage

```tsx
import Calendar from '../components/calendar/Calendar';

const events = [
  {
    id: '1',
    title: 'Incident Shift',
    start: '2025-01-08T08:00:00',
    end: '2025-01-08T17:00:00',
    extendedProps: {
      shiftType: 'incident',
      engineerName: 'John Doe',
      engineerId: 'user1',
      status: 'confirmed',
    },
  }
];

<Calendar
  events={events}
  onEventDrop={(info) => handleSwapRequest(info)}
  onEventClick={(info) => showEventDetails(info)}
  onDateSelect={(info) => createNewShift(info)}
/>
```

## Props

- `events: CalendarEvent[]` - Array of calendar events to display
- `onEventDrop?: (info: EventDropArg) => void` - Handler for drag-drop events
- `onEventClick?: (info: EventClickArg) => void` - Handler for event clicks
- `onDateSelect?: (info: DateSelectArg) => void` - Handler for date selection

## Next Phase Features

- **Resource Timeline** - Engineer-based timeline view
- **WebSocket Integration** - Real-time collaborative updates
- **Advanced Filtering** - Team-based filters
- **Bulk Operations** - Multi-select and batch actions
