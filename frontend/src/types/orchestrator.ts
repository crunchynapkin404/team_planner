// TypeScript type definitions for Orchestrator V2 Clean Architecture API

export interface ScheduleRequest {
  start_date: string; // YYYY-MM-DD format
  end_date: string;   // YYYY-MM-DD format
  department_id?: string;
  options?: {
    dry_run?: boolean;
    force?: boolean;
  };
}

export interface OrchestrationResult {
  success: boolean;
  statistics: {
    assignments_made: number;
    unassigned_shifts: number;
    conflicts_detected: number;
    warnings: number;
  };
  assignments: Assignment[];
  conflicts: Conflict[];
  warnings: string[];
  execution_time?: number;
}

export interface Assignment {
  assignment_id: string;
  shift_id: number;
  employee_id: number;
  employee_name?: string;
  auto_assigned: boolean;
  shift_type: string;
  start_datetime: string;
  end_datetime: string;
}

export interface Conflict {
  conflict_id: string;
  type: 'leave_conflict' | 'availability_conflict' | 'rest_period_violation' | 'consecutive_weeks_violation';
  description: string;
  shift_id: number;
  employee_id: number;
  severity: 'warning' | 'error' | 'info';
}

export interface CoverageAnalysis {
  date_range: {
    start_date: string;
    end_date: string;
  };
  coverage_by_date: Record<string, DailyCoverage>;
  summary: {
    total_days: number;
    days_with_coverage: number;
    days_without_coverage: number;
    coverage_percentage: number;
  };
}

export interface DailyCoverage {
  [shiftType: string]: {
    total_shifts: number;
    assigned_shifts: number;
    unassigned_shifts: number;
    assignments: Assignment[];
  };
}

export interface AvailabilityParams {
  start_date: string;
  end_date: string;
  shift_type?: 'incidents' | 'waakdienst' | 'incidents_standby';
  department_id?: string;
}

export interface EmployeeAvailability {
  employee_id: number;
  name: string;
  email: string;
  available_for_incidents: boolean;
  available_for_waakdienst: boolean;
  current_assignments_count: number;
  fairness_score?: number;
  last_assignment_date?: string;
}

export interface AvailabilityResponse {
  time_range: {
    start: string;
    end: string;
  };
  shift_type?: string;
  available_employees: EmployeeAvailability[];
  total_available: number;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  components: {
    database: 'healthy' | 'degraded' | 'unhealthy';
    orchestrator: 'healthy' | 'degraded' | 'unhealthy';
    cache: 'healthy' | 'degraded' | 'unhealthy';
  };
  response_time_ms?: number;
}

export interface SystemMetrics {
  total_active_employees: number;
  total_shifts_last_30_days: number;
  assigned_shifts_last_30_days: number;
  assignment_rate_percentage: number;
  unassigned_shifts_last_30_days: number;
  average_orchestration_time_seconds: number;
  timestamp: string;
}

// API Response wrapper types
export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface ApiError {
  error: string;
  details?: Record<string, string[]>;
  status: number;
  timestamp: string;
}

// Form types for React components
export interface OrchestratorFormData {
  dateRange: {
    startDate: Date | null;
    endDate: Date | null;
  };
  departmentId: string | null;
  shiftTypes: string[];
  options: {
    dryRun: boolean;
    force: boolean;
    includeStandby: boolean;
  };
}

export interface CoverageFilterData {
  dateRange: {
    startDate: Date | null;
    endDate: Date | null;
  };
  departmentId?: string;
  shiftType?: string;
}

export interface AvailabilityFilterData {
  dateRange: {
    startDate: Date | null;
    endDate: Date | null;
  };
  shiftType?: string;
  departmentId?: string;
}

// Component state types
export interface OrchestratorState {
  // Orchestration state
  orchestrationStatus: 'idle' | 'running' | 'success' | 'error';
  lastOrchestration: OrchestrationResult | null;
  orchestrationHistory: OrchestrationResult[];
  
  // Coverage state
  coverageData: CoverageAnalysis | null;
  coverageLoading: boolean;
  
  // Availability state
  availabilityData: EmployeeAvailability[];
  availabilityLoading: boolean;
  
  // System monitoring
  systemHealth: SystemHealth | null;
  systemMetrics: SystemMetrics | null;
  
  // UI state
  loading: boolean;
  error: string | null;
  selectedDateRange: { start: Date | null; end: Date | null };
  selectedDepartment: string | null;
}

// Hook return types
export interface UseOrchestratorReturn {
  // State
  state: OrchestratorState;
  
  // Core Actions
  scheduleOrchestration: (request: ScheduleRequest) => Promise<OrchestrationResult>;
  getCoverage: (params: { start_date: string; end_date: string; department_id?: string }) => Promise<CoverageAnalysis>;
  getAvailability: (params: AvailabilityParams) => Promise<AvailabilityResponse>;
  refreshSystemHealth: () => Promise<SystemHealth>;
  refreshMetrics: () => Promise<SystemMetrics>;
  
  // UI Actions
  clearError: () => void;
  updateSelectedDateRange: (dateRange: { start: Date | null; end: Date | null }) => void;
  updateSelectedDepartment: (departmentId: string | null) => void;
  clearHistory: () => void;
  clearCoverage: () => void;
  clearAvailability: () => void;
  resetState: () => void;
  
  // Convenience Actions
  scheduleCurrentWeek: (departmentId?: string, options?: { dry_run?: boolean; force?: boolean }) => Promise<OrchestrationResult>;
  scheduleNextWeek: (departmentId?: string, options?: { dry_run?: boolean; force?: boolean }) => Promise<OrchestrationResult>;
  scheduleCustomDateRange: (startDate: Date, endDate: Date, departmentId?: string, options?: { dry_run?: boolean; force?: boolean }) => Promise<OrchestrationResult>;
  getCoverageForCurrentWeek: (departmentId?: string) => Promise<CoverageAnalysis>;
  getCoverageForNextWeek: (departmentId?: string) => Promise<CoverageAnalysis>;
  getCoverageForCustomRange: (startDate: Date, endDate: Date, departmentId?: string) => Promise<CoverageAnalysis>;
  getAvailabilityForCurrentWeek: (shiftType?: string, departmentId?: string) => Promise<AvailabilityResponse>;
  
  // Status Checks
  isLoading: boolean;
  hasError: boolean;
  isOrchestrationRunning: boolean;
  hasLastOrchestration: boolean;
  isSystemHealthy: boolean;
  
  // Summary Functions
  getOrchestrationSummary: () => string | null;
  getCoverageSummary: () => string | null;
}

// Utility types
export type ShiftType = 'incidents' | 'incidents_standby' | 'waakdienst';
export type OrchestrationStatus = 'idle' | 'running' | 'success' | 'error';
export type SystemStatus = 'healthy' | 'degraded' | 'unhealthy';

// Constants
export const SHIFT_TYPES = {
  INCIDENTS: 'incidents' as const,
  INCIDENTS_STANDBY: 'incidents_standby' as const,
  WAAKDIENST: 'waakdienst' as const,
} as const;

export const ORCHESTRATION_STATUS = {
  IDLE: 'idle' as const,
  RUNNING: 'running' as const,
  SUCCESS: 'success' as const,
  ERROR: 'error' as const,
} as const;
