import { apiClient } from './apiClient';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  teams: Team[];
  permissions: string[];
}

export interface Team {
  id: number;
  name: string;
  role: string;
}

export interface TeamMember {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  display_name: string;
}

export interface UserShift {
  id: number;
  title: string;
  start_time: string;
  end_time: string;
  shift_type: string;
  status: string;
  is_upcoming: boolean;
}

export interface SwapRequest {
  id: number;
  requester: {
    id: number;
    username: string;
    first_name?: string;
    last_name?: string;
  };
  target_employee: {
    id: number;
    username: string;
    first_name?: string;
    last_name?: string;
  };
  requesting_shift: {
    id: number;
    title: string;
    start_time: string;
    end_time: string;
    shift_type: string;
  };
  target_shift?: {
    id: number;
    title: string;
    start_time: string;
    end_time: string;
    shift_type: string;
  };
  reason: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  response_notes?: string;
  created_at: string;
  approved_by?: {
    username: string;
    first_name?: string;
    last_name?: string;
  };
  approved_datetime?: string;
}

export interface UserDashboardData {
  upcoming_shifts: UserShift[];
  incoming_swap_requests: SwapRequest[];
  outgoing_swap_requests: SwapRequest[];
  recent_activities: Activity[];
  shift_stats: {
    total_shifts_this_month: number;
    completed_shifts: number;
    upcoming_shifts: number;
    swap_requests_pending: number;
  };
}

export interface Activity {
  id: number;
  type: 'shift' | 'swap_request' | 'leave_request' | 'orchestration';
  message: string;
  status: 'pending' | 'approved' | 'rejected' | 'completed' | 'info';
  created_at: string;
  related_object_id?: number;
}

export interface BulkSwapRequest {
  shifts: {
    requesting_shift_id: number;
    target_employee_id: number;
    target_shift_id?: number;
  }[];
  reason: string;
  swap_type: 'with_specific_shifts' | 'any_available' | 'schedule_takeover';
}

export interface BulkSwapResponse {
  success: boolean;
  created_requests: number[];
  failed_requests: {
    requesting_shift_id: number;
    error: string;
  }[];
  message: string;
}

export const userService = {
  getCurrentUser: async (): Promise<User> => {
    return apiClient.get('/api/users/me/');
  },

  getUserDashboardData: async (): Promise<UserDashboardData> => {
    return apiClient.get('/api/users/me/dashboard/');
  },

  getUpcomingShifts: async (limit: number = 5): Promise<UserShift[]> => {
    return apiClient.get(`/shifts/api/user/upcoming-shifts/?limit=${limit}`);
  },

  getIncomingSwapRequests: async (): Promise<SwapRequest[]> => {
    return apiClient.get('/shifts/api/user/incoming-swap-requests/');
  },

  getOutgoingSwapRequests: async (): Promise<SwapRequest[]> => {
    return apiClient.get('/shifts/api/user/outgoing-swap-requests/');
  },

  respondToSwapRequest: async (requestId: number, action: 'approve' | 'reject', message?: string): Promise<void> => {
    return apiClient.post(`/shifts/api/swap-requests/${requestId}/respond/`, {
      action,
      message,
    });
  },

  createSwapRequest: async (data: {
    requesting_shift_id: number;
    target_employee_id: number;
    target_shift_id?: number;
    reason: string;
  }): Promise<{ message: string; swap_request_id: number }> => {
    return apiClient.post('/shifts/api/swap-requests/create/', data);
  },

  createBulkSwapRequest: async (data: BulkSwapRequest): Promise<BulkSwapResponse> => {
    return apiClient.post('/shifts/api/swap-requests/bulk-create/', data);
  },

  getUserShifts: async (): Promise<UserShift[]> => {
    return apiClient.get('/shifts/api/user/shifts/');
  },

  getTeamMembers: async (): Promise<TeamMember[]> => {
    return apiClient.get('/shifts/api/team-members/');
  },

  getEmployeeShifts: async (employeeId: number): Promise<UserShift[]> => {
    return apiClient.get(`/shifts/api/employee-shifts/?employee_id=${employeeId}`);
  },

  hasPermission: (user: User, permission: string): boolean => {
    return user.permissions?.includes(permission) || user.is_superuser;
  },

  canAccessOrchestrator: (user: User): boolean => {
    return userService.hasPermission(user, 'orchestrators.view_orchestration') || 
           user.is_staff || user.is_superuser;
  },

  canAccessUserManagement: (user: User): boolean => {
    return userService.hasPermission(user, 'users.view_user') || 
           user.is_staff || user.is_superuser;
  },

  canAccessTeamManagement: (user: User): boolean => {
    return userService.hasPermission(user, 'teams.view_team') || 
           user.is_staff || user.is_superuser;
  },
};
