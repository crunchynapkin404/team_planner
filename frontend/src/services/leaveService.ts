import { apiClient } from './apiClient';
import { API_CONFIG, buildEndpointUrl } from '../config/api';
import { formatDate } from '../utils/dateUtils';

export interface LeaveType {
  id: number;
  name: string;
  description: string;
  color: string;
  default_days_per_year?: number;
  requires_approval: boolean;
  is_paid: boolean;
  is_active: boolean;
  conflict_handling: 'full_unavailable' | 'daytime_only' | 'no_conflict';
  conflict_handling_display: string;
  start_time?: string;
  end_time?: string;
}

export interface Employee {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  display_name: string;
  available_incidents?: boolean;
  available_waakdienst?: boolean;
}

export interface ConflictingShift {
  id: number;
  start_datetime: string;
  end_datetime: string;
  shift_type: string;
  shift_name: string;
  status: string;
  duration_hours: number;
  notes: string;
}

export interface ConflictingShiftsResponse {
  leave_request_id: number;
  conflicts_count: number;
  conflicting_shifts: ConflictingShift[];
}

export interface LeaveRequest {
  id: number;
  employee: Employee;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  start_time?: string;
  end_time?: string;
  effective_start_time?: string;
  effective_end_time?: string;
  days_requested: number;
  reason: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  status_display: string;
  has_shift_conflicts: boolean;
  can_be_approved: boolean;
  blocking_message?: string;
  within_active_window?: boolean;
  approved_by?: Employee;
  approved_at?: string;
  rejection_reason?: string;
  created: string;
  modified: string;
  conflicting_shifts?: ConflictingShift[];
  suggested_employees?: Employee[];
  
  // Recurring leave fields
  is_recurring: boolean;
  recurrence_type: 'none' | 'weekly' | 'monthly' | 'custom';
  recurrence_type_display: string;
  recurrence_end_date?: string;
  parent_request?: number;
}

export interface LeaveRequestsResponse {
  results: LeaveRequest[];
  count: number;
  total_pages: number;
  current_page: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface CreateLeaveRequestData {
  leave_type_id: number;
  start_date: string;
  end_date: string;
  start_time?: string;
  end_time?: string;
  days_requested: number;
  reason: string;
  is_recurring?: boolean;
  recurrence_type?: 'none' | 'weekly' | 'monthly' | 'custom';
  recurrence_end_date?: string;
}

export interface CreateLeaveRequestResponse {
  id: number;
  message: string;
  has_conflicts: boolean;
  conflict_warning?: string;
}

export interface ConflictCheckResponse {
  conflicts: ConflictingShift[];
  suggestions: Employee[];
  has_conflicts: boolean;
  message?: string;
}

export interface LeaveStats {
  total_requests: number;
  pending_requests: number;
  approved_requests: number;
  rejected_requests: number;
  days_used_this_year: number;
  current_year: number;
}

export interface LeaveRequestFilters {
  employee_id?: number;
  leave_type_id?: number;
  status?: string;
  start_date_from?: string;
  start_date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const leaveService = {
  // Get leave requests with filters and pagination
  getLeaveRequests: async (filters: LeaveRequestFilters = {}): Promise<LeaveRequestsResponse> => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString());
      }
    });
    
    return apiClient.get(`${API_CONFIG.ENDPOINTS.LEAVES_REQUESTS}?${params.toString()}`);
  },

  // Get a specific leave request with full details
  getLeaveRequest: async (id: number): Promise<LeaveRequest> => {
    const url = buildEndpointUrl(API_CONFIG.ENDPOINTS.LEAVES_REQUEST_DETAIL, { id });
    return apiClient.get(url);
  },

  // Create a new leave request
  createLeaveRequest: async (data: CreateLeaveRequestData): Promise<CreateLeaveRequestResponse> => {
    return apiClient.post(API_CONFIG.ENDPOINTS.LEAVES_REQUEST_CREATE, data);
  },

  // Approve a leave request
  approveLeaveRequest: async (id: number): Promise<{ message: string; status: string }> => {
    const url = buildEndpointUrl(API_CONFIG.ENDPOINTS.LEAVES_REQUEST_APPROVE, { id });
    return apiClient.post(url);
  },

  // Reject a leave request
  rejectLeaveRequest: async (id: number, rejectionReason: string): Promise<{ message: string; status: string }> => {
    const url = buildEndpointUrl(API_CONFIG.ENDPOINTS.LEAVES_REQUEST_REJECT, { id });
    return apiClient.post(url, {
      rejection_reason: rejectionReason,
    });
  },

  // Cancel a leave request
  cancelLeaveRequest: async (id: number): Promise<{ message: string; status: string }> => {
    const url = buildEndpointUrl(API_CONFIG.ENDPOINTS.LEAVES_REQUEST_CANCEL, { id });
    return apiClient.post(url);
  },

  // Get available leave types
  getLeaveTypes: async (): Promise<LeaveType[]> => {
    const response = await apiClient.get(API_CONFIG.ENDPOINTS.LEAVES_TYPES) as any;
    // Handle paginated response format
    return response.results || response;
  },

  // Get conflicting shifts for a leave request
  getConflictingShifts: async (leaveRequestId: number): Promise<ConflictingShiftsResponse> => {
    const url = buildEndpointUrl(API_CONFIG.ENDPOINTS.LEAVES_CONFLICTING_SHIFTS, { id: leaveRequestId });
    return apiClient.get(url);
  },

  // Check for conflicts when creating a leave request
  checkConflicts: async (startDate: string, endDate: string): Promise<ConflictCheckResponse> => {
    return apiClient.get(`${API_CONFIG.ENDPOINTS.LEAVES_CHECK_CONFLICTS}?start_date=${startDate}&end_date=${endDate}`);
  },

  // Get user's leave statistics
  getUserStats: async (): Promise<LeaveStats> => {
    return apiClient.get(API_CONFIG.ENDPOINTS.LEAVES_USER_STATS);
  },

  // Helper methods
  getStatusColor: (status: string): string => {
    switch (status) {
      case 'pending':
        return '#ffc107'; // warning yellow
      case 'approved':
        return '#28a745'; // success green
      case 'rejected':
        return '#dc3545'; // danger red
      case 'cancelled':
        return '#6c757d'; // secondary gray
      default:
        return '#007bff'; // primary blue
    }
  },

  getStatusIcon: (status: string): string => {
    switch (status) {
      case 'pending':
        return 'schedule';
      case 'approved':
        return 'check_circle';
      case 'rejected':
        return 'cancel';
      case 'cancelled':
        return 'block';
      default:
        return 'help';
    }
  },

  formatDateRange: (startDate: string, endDate: string): string => {
    const start = new Date(startDate);
    const end = new Date(endDate);

    if (start.toDateString() === end.toDateString()) {
      return formatDate(start);
    }
    
    if (start.getFullYear() === end.getFullYear() && start.getMonth() === end.getMonth()) {
      return `${start.getDate()} - ${end.getDate()}/${(start.getMonth() + 1).toString().padStart(2, '0')}/${start.getFullYear()}`;
    }
    
    return `${formatDate(start)} - ${formatDate(end)}`;
  },

  calculateDays: (startDate: string, endDate: string): number => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // +1 to include both start and end dates
    return diffDays;
  },
};
