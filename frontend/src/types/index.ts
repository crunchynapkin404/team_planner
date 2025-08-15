// User types
export interface User {
  id: number;
  username: string;
  email: string;
  name: string;
  url: string;
}

// Authentication types
export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface SignupCredentials {
  username: string;
  email: string;
  password1: string;
  password2: string;
}

// API Response types
export interface ApiError {
  message: string;
  status: number;
  data?: any;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

// Employee types
export interface Employee {
  id: number;
  user: User;
  status: 'active' | 'inactive';
  hire_date: string;
  skills: string[];
  created_at: string;
  updated_at: string;
}

// Team types
export interface Team {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

// Shift types
export interface Shift {
  id: number;
  date: string;
  start_time: string;
  end_time: string;
  role: string;
  employee: Employee | null;
  team: Team;
  status: 'scheduled' | 'completed' | 'cancelled';
  created_at: string;
  updated_at: string;
}

// Leave types
export interface LeaveRequest {
  id: number;
  employee: Employee;
  start_date: string;
  end_date: string;
  reason: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  updated_at: string;
}

// Swap Request types
export interface SwapRequest {
  id: number;
  requester: Employee;
  original_shift: Shift;
  target_employee: Employee | null;
  target_shift: Shift | null;
  reason: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  fairness_score: number;
  created_at: string;
  updated_at: string;
}

// Orchestration types
export interface Orchestration {
  id: number;
  name: string;
  shift_type: string;
  start_date: string;
  end_date: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  fairness_enabled: boolean;
  result_summary: any;
  applied: boolean;
  created_at: string;
  updated_at: string;
}

// Recurring Leave Pattern types
export interface RecurringLeavePattern {
  id: number;
  employee: number;
  name: string;
  day_of_week: number;
  frequency: 'weekly' | 'biweekly';
  coverage_type: 'full_day' | 'morning' | 'afternoon';
  pattern_start_date: string;
  effective_from: string;
  effective_until?: string;
  is_active: boolean;
  notes: string;
  created: string;
  modified: string;
}

export interface RecurringLeavePatternForm {
  name: string;
  day_of_week: number;
  frequency: 'weekly' | 'biweekly';
  coverage_type: 'full_day' | 'morning' | 'afternoon';
  pattern_start_date: string;
  effective_from: string;
  effective_until?: string;
  is_active: boolean;
  notes: string;
}
