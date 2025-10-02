import { apiClient } from './apiClient';

// ============================================================================
// Type Definitions
// ============================================================================

export interface ConflictCheckRequest {
  employee_id: number;
  start_date: string;
  end_date: string;
  team_id?: number;
  department_id?: number;
}

export interface PersonalConflict {
  id: number;
  start_date: string;
  end_date: string;
  status: string;
  leave_type: string;
  days_requested: number;
}

export interface ConflictDay {
  date: string;
  leave_count: number;
  employees_on_leave: number[];
}

export interface StaffingDay {
  date: string;
  available_staff: number;
  required_staff: number;
  shortage: number;
}

export interface ShiftConflict {
  id: number;
  shift_date: string;
  shift_type: string;
  start_time: string;
  end_time: string;
}

export interface StaffingAnalysis {
  understaffed_days: StaffingDay[];
  warning_days: StaffingDay[];
  total_team_size: number;
}

export interface ConflictCheckResponse {
  has_conflicts: boolean;
  personal_conflicts: PersonalConflict[];
  team_conflicts_by_day: {
    conflict_days: ConflictDay[];
  };
  staffing_analysis: StaffingAnalysis;
  shift_conflicts: ShiftConflict[];
}

export interface AlternativeDateRequest {
  employee_id: number;
  start_date: string;
  days_requested: number;
  team_id?: number;
  department_id?: number;
}

export interface AlternativeSuggestion {
  start_date: string;
  end_date: string;
  conflict_score: number;
  is_understaffed: boolean;
  days_offset: number;
}

export interface AlternativeDatesResponse {
  suggestions: AlternativeSuggestion[];
}

export interface ConflictDashboardParams {
  start_date: string;
  end_date: string;
  team_id?: number;
  department_id?: number;
}

export interface ConflictDashboard {
  conflict_days: ConflictDay[];
  understaffed_days: StaffingDay[];
  warning_days: StaffingDay[];
  total_team_size: number;
}

export interface ResolutionRequest {
  approve_request_id: number;
  reject_request_ids: number[];
  resolution_notes: string;
}

export interface ResolutionResult {
  approved_request_id: number;
  rejected_request_ids: number[];
  resolved_by: string;
  resolution_notes: string;
}

export interface RecommendationRequest {
  request_ids: number[];
}

export interface RequestRecommendation {
  id: number;
  employee: string;
  start_date: string;
  end_date: string;
  days_requested: number;
}

export interface RecommendationDetails {
  seniority?: {
    id: number;
    reason: string;
  };
  first_request?: {
    id: number;
    reason: string;
  };
  leave_balance?: {
    id: number;
    reason: string;
  };
}

export interface Recommendation {
  recommended_request: RequestRecommendation;
  recommendation_details: RecommendationDetails;
  vote_counts: Record<number, number>;
  alternatives: number[];
}

// ============================================================================
// Service Class
// ============================================================================

class LeaveConflictService {
  /**
   * Check for conflicts before creating a leave request
   */
  async checkConflicts(data: ConflictCheckRequest): Promise<ConflictCheckResponse> {
    return await apiClient.post<ConflictCheckResponse>(
      '/api/leaves/check-conflicts/',
      data
    );
  }

  /**
   * Get alternative date suggestions
   */
  async suggestAlternatives(data: AlternativeDateRequest): Promise<AlternativeSuggestion[]> {
    const response = await apiClient.post<AlternativeDatesResponse>(
      '/api/leaves/suggest-alternatives/',
      data
    );
    return response.suggestions;
  }

  /**
   * Get all conflicting requests (manager view)
   */
  async getConflicts(params: ConflictDashboardParams): Promise<ConflictDashboard> {
    return await apiClient.get<ConflictDashboard>('/api/leaves/conflicts/', {
      params,
    });
  }

  /**
   * Resolve a conflict by approving one request and rejecting others
   */
  async resolveConflict(data: ResolutionRequest): Promise<ResolutionResult> {
    return await apiClient.post<ResolutionResult>(
      '/api/leaves/resolve-conflict/',
      data
    );
  }

  /**
   * Get AI-style recommendation for resolving conflicts
   */
  async getRecommendation(requestIds: number[]): Promise<Recommendation> {
    return await apiClient.post<Recommendation>(
      '/api/leaves/recommend-resolution/',
      { request_ids: requestIds }
    );
  }
}

export default new LeaveConflictService();
