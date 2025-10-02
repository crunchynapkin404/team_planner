/**
 * Report API service
 */
import { apiClient } from './apiClient';

export interface ScheduleShift {
  id: number;
  date: string;
  start_time: string;
  end_time: string;
  employee_id: number;
  employee_name: string;
  shift_type: string;
  status: string;
  auto_assigned: boolean;
}

export interface ScheduleReport {
  start_date: string;
  end_date: string;
  total_shifts: number;
  shifts: ScheduleShift[];
}

export interface FairnessEmployee {
  employee_id: number;
  employee_name: string;
  fte: number;
  total_shifts: number;
  total_hours: number;
  incidents_count: number;
  waakdienst_count: number;
  standby_count: number;
  hours_per_fte: number;
}

export interface FairnessReport {
  start_date: string;
  end_date: string;
  team_id: number | null;
  employee_count: number;
  average_hours_per_fte: number;
  max_hours_per_fte: number;
  min_hours_per_fte: number;
  variance: number;
  distribution: FairnessEmployee[];
}

export interface LeaveBalance {
  employee_id: number;
  employee_name: string;
  leave_type: string;
  total_days: number;
  used_days: number;
  remaining_days: number;
  is_exhausted: boolean;
}

export interface LeaveBalanceReport {
  year: number;
  total_balances: number;
  balances: LeaveBalance[];
}

export interface SwapHistoryItem {
  id: number;
  created_date: string;
  requesting_employee: string;
  target_employee: string;
  requesting_shift_date: string;
  target_shift_date: string | null;
  status: string;
  approved_date: string | null;
}

export interface SwapHistoryReport {
  start_date: string;
  end_date: string;
  total_swaps: number;
  approved_count: number;
  rejected_count: number;
  pending_count: number;
  approval_rate: number;
  swaps: SwapHistoryItem[];
}

export interface EmployeeHours {
  employee_id: number;
  employee_name: string;
  total_hours: number;
  incidents_hours: number;
  waakdienst_hours: number;
  shift_count: number;
}

export interface EmployeeHoursReport {
  start_date: string;
  end_date: string;
  employee_count: number;
  total_hours: number;
  hours: EmployeeHours[];
}

export interface WeekendHolidayEmployee {
  employee_id: number;
  employee_name: string;
  weekend_shifts: number;
  holiday_shifts: number;
  total_special_shifts: number;
}

export interface WeekendHolidayReport {
  start_date: string;
  end_date: string;
  team_id: number | null;
  employee_count: number;
  total_weekend_shifts: number;
  total_holiday_shifts: number;
  distribution: WeekendHolidayEmployee[];
}

export interface ReportFilters {
  start_date?: string;
  end_date?: string;
  team_id?: number;
  department_id?: number;
  employee_id?: number;
  year?: number;
}

export const reportService = {
  /**
   * Get schedule report
   */
  async getScheduleReport(filters: ReportFilters): Promise<ScheduleReport> {
    const params = new URLSearchParams();
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.team_id) params.append('team_id', filters.team_id.toString());
    if (filters.department_id) params.append('department_id', filters.department_id.toString());

    const response: any = await apiClient.get(`/reports/schedule/?${params.toString()}`);
    return response;
  },

  /**
   * Get fairness distribution report
   */
  async getFairnessReport(filters: ReportFilters): Promise<FairnessReport> {
    const params = new URLSearchParams();
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.team_id) params.append('team_id', filters.team_id.toString());

    const response: any = await apiClient.get(`/reports/fairness/?${params.toString()}`);
    return response;
  },

  /**
   * Get leave balance report
   */
  async getLeaveBalanceReport(filters: ReportFilters): Promise<LeaveBalanceReport> {
    const params = new URLSearchParams();
    if (filters.employee_id) params.append('employee_id', filters.employee_id.toString());
    if (filters.team_id) params.append('team_id', filters.team_id.toString());
    if (filters.year) params.append('year', filters.year.toString());

    const response: any = await apiClient.get(`/reports/leave-balance/?${params.toString()}`);
    return response;
  },

  /**
   * Get swap history report
   */
  async getSwapHistoryReport(filters: ReportFilters): Promise<SwapHistoryReport> {
    const params = new URLSearchParams();
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.employee_id) params.append('employee_id', filters.employee_id.toString());
    if (filters.team_id) params.append('team_id', filters.team_id.toString());

    const response: any = await apiClient.get(`/reports/swap-history/?${params.toString()}`);
    return response;
  },

  /**
   * Get employee hours report
   */
  async getEmployeeHoursReport(filters: ReportFilters): Promise<EmployeeHoursReport> {
    const params = new URLSearchParams();
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.employee_id) params.append('employee_id', filters.employee_id.toString());
    if (filters.team_id) params.append('team_id', filters.team_id.toString());

    const response: any = await apiClient.get(`/reports/employee-hours/?${params.toString()}`);
    return response;
  },

  /**
   * Get weekend/holiday distribution report
   */
  async getWeekendHolidayReport(filters: ReportFilters): Promise<WeekendHolidayReport> {
    const params = new URLSearchParams();
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.team_id) params.append('team_id', filters.team_id.toString());

    const response: any = await apiClient.get(`/reports/weekend-holiday/?${params.toString()}`);
    return response;
  },
};
