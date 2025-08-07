// Calendar and Shift related types
export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  resourceId?: string;
  backgroundColor?: string;
  borderColor?: string;
  extendedProps?: {
    shiftType?: 'incident' | 'waakdienst' | 'project' | 'change';
    leaveType?: 'vacation' | 'sick' | 'personal' | 'other';
    engineerName: string;
    engineerId: string;
    status: 'confirmed' | 'pending' | 'swap_requested' | 'approved' | 'rejected' | 'cancelled';
    teamId?: string;
    teamName?: string;
    eventType: 'shift' | 'leave';
    reason?: string;
    days_requested?: number;
    leave_type_name?: string;
    leave_type_color?: string;
  };
}

export interface CalendarResource {
  id: string;
  title: string;
  group?: string;
}

// Shift Types
export type ShiftType = 'incident' | 'waakdienst' | 'project' | 'change';
export type ShiftStatus = 'confirmed' | 'pending' | 'swap_requested';

// Engineer/Employee Types
export interface Engineer {
  id: string;
  name: string;
  email: string;
  teamId: string;
  teamName: string;
  availableForIncidents: boolean;
  availableForWaakdienst: boolean;
}

// Swap Request Types
export interface SwapRequest {
  id: string;
  fromEngineerId: string;
  toEngineerId: string;
  shiftId: string;
  requestDate: string;
  status: 'pending' | 'approved' | 'rejected';
  reason?: string;
  responseDate?: string;
}

// Leave Request Types
export interface LeaveRequest {
  id: string;
  engineerId: string;
  startDate: string;
  endDate: string;
  leaveType: 'vacation' | 'sick' | 'personal' | 'emergency';
  status: 'pending' | 'approved' | 'rejected';
  reason?: string;
  conflictingShifts?: string[];
}

// Team Types
export interface Team {
  id: string;
  name: string;
  leaderId: string;
  members: Engineer[];
}

// Orchestration Types
export interface OrchestrationRun {
  id: string;
  startDate: string;
  endDate: string;
  status: 'running' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
  shiftsGenerated: number;
  fairnessScore: number;
}
