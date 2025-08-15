/**
 * Orchestrator Service - Clean Architecture API Integration
 * Provides service functions for interacting with the orchestrator V2 API endpoints
 */

import { apiClient } from './apiClient';
import { API_CONFIG } from '../config/api';
import type {
  ScheduleRequest,
  OrchestrationResult,
  CoverageAnalysis,
  AvailabilityParams,
  AvailabilityResponse,
  SystemHealth,
  SystemMetrics,
  ApiError,
} from '../types/orchestrator';

export class OrchestratorService {
  /**
   * Schedule orchestration for a given date range and department
   */
  static async scheduleOrchestration(request: ScheduleRequest): Promise<OrchestrationResult> {
    try {
      const response = await apiClient.post<OrchestrationResult>(
        API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_SCHEDULE,
        request
      );
      return response;
    } catch (error) {
      throw this.handleApiError(error, 'Failed to schedule orchestration');
    }
  }

  /**
   * Get shift coverage analysis for a date range
   */
  static async getCoverage(params: {
    start_date: string;
    end_date: string;
    department_id?: string;
  }): Promise<CoverageAnalysis> {
    try {
      const response = await apiClient.get<CoverageAnalysis>(
        API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_COVERAGE,
        { params }
      );
      return response;
    } catch (error) {
      throw this.handleApiError(error, 'Failed to get coverage data');
    }
  }

  /**
   * Get employee availability for a time range and shift type
   */
  static async getAvailability(params: AvailabilityParams): Promise<AvailabilityResponse> {
    try {
      const response = await apiClient.get<AvailabilityResponse>(
        API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_AVAILABILITY,
        { params }
      );
      return response;
    } catch (error) {
      throw this.handleApiError(error, 'Failed to get availability data');
    }
  }

  /**
   * Get system health status
   */
  static async getSystemHealth(): Promise<SystemHealth> {
    try {
      const response = await apiClient.get<SystemHealth>(
        API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_HEALTH
      );
      return response;
    } catch (error) {
      throw this.handleApiError(error, 'Failed to get system health');
    }
  }

  /**
   * Get system metrics and statistics
   */
  static async getSystemMetrics(): Promise<SystemMetrics> {
    try {
      const response = await apiClient.get<SystemMetrics>(
        API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_METRICS
      );
      return response;
    } catch (error) {
      throw this.handleApiError(error, 'Failed to get system metrics');
    }
  }

  /**
   * Format date to YYYY-MM-DD string for API calls
   */
  static formatDateForApi(date: Date): string {
    return date.toISOString().split('T')[0];
  }

  /**
   * Get current week date range (Monday to Friday)
   */
  static getCurrentWeekRange(): { start_date: string; end_date: string } {
    const today = new Date();
    const monday = new Date(today);
    const friday = new Date(today);
    
    // Calculate Monday of current week
    const dayOfWeek = today.getDay();
    const daysFromMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // Sunday = 0
    monday.setDate(today.getDate() - daysFromMonday);
    
    // Calculate Friday of current week
    friday.setDate(monday.getDate() + 4);
    
    return {
      start_date: this.formatDateForApi(monday),
      end_date: this.formatDateForApi(friday),
    };
  }

  /**
   * Get next week date range (Monday to Friday)
   */
  static getNextWeekRange(): { start_date: string; end_date: string } {
    const currentWeek = this.getCurrentWeekRange();
    const nextMonday = new Date(currentWeek.start_date);
    const nextFriday = new Date(currentWeek.end_date);
    
    nextMonday.setDate(nextMonday.getDate() + 7);
    nextFriday.setDate(nextFriday.getDate() + 7);
    
    return {
      start_date: this.formatDateForApi(nextMonday),
      end_date: this.formatDateForApi(nextFriday),
    };
  }

  /**
   * Get custom date range
   */
  static getCustomDateRange(startDate: Date, endDate: Date): { start_date: string; end_date: string } {
    return {
      start_date: this.formatDateForApi(startDate),
      end_date: this.formatDateForApi(endDate),
    };
  }

  /**
   * Validate orchestration request
   */
  static validateScheduleRequest(request: ScheduleRequest): string[] {
    const errors: string[] = [];
    
    if (!request.start_date) {
      errors.push('Start date is required');
    }
    
    if (!request.end_date) {
      errors.push('End date is required');
    }
    
    if (request.start_date && request.end_date) {
      const startDate = new Date(request.start_date);
      const endDate = new Date(request.end_date);
      
      if (startDate >= endDate) {
        errors.push('End date must be after start date');
      }
      
      const maxRange = 30; // days
      const diffTime = Math.abs(endDate.getTime() - startDate.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays > maxRange) {
        errors.push(`Date range cannot exceed ${maxRange} days`);
      }
    }
    
    return errors;
  }

  /**
   * Check if orchestration is in progress
   */
  static isOrchestrationInProgress(_result: OrchestrationResult | null): boolean {
    return false; // Since our API is synchronous, this would be managed by component state
  }

  /**
   * Get orchestration summary text
   */
  static getOrchestrationSummary(result: OrchestrationResult): string {
    if (!result) return 'No orchestration data available';
    
    const { statistics } = result;
    const total = statistics.assignments_made + statistics.unassigned_shifts;
    const successRate = total > 0 ? Math.round((statistics.assignments_made / total) * 100) : 0;
    
    return `${statistics.assignments_made} assignments made, ${statistics.unassigned_shifts} unassigned shifts, ${successRate}% success rate`;
  }

  /**
   * Get coverage summary text
   */
  static getCoverageSummary(coverage: CoverageAnalysis): string {
    if (!coverage) return 'No coverage data available';
    
    const { summary } = coverage;
    const coveragePercent = Math.round(summary.coverage_percentage || 0);
    
    return `${summary.days_with_coverage}/${summary.total_days} days covered (${coveragePercent}%)`;
  }

  /**
   * Handle API errors consistently
   */
  private static handleApiError(error: any, defaultMessage: string): Error {
    if (error.response?.data) {
      const apiError = error.response.data as ApiError;
      const message = apiError.error || defaultMessage;
      const details = apiError.details ? Object.values(apiError.details).flat().join(', ') : '';
      return new Error(details ? `${message}: ${details}` : message);
    }
    
    if (error.message) {
      return new Error(`${defaultMessage}: ${error.message}`);
    }
    
    return new Error(defaultMessage);
  }

  /**
   * Parse ISO date string to local Date object
   */
  static parseApiDate(dateString: string): Date {
    return new Date(dateString);
  }

  /**
   * Format duration in seconds to human readable format
   */
  static formatDuration(seconds: number): string {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.round((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  }

  /**
   * Get color for orchestration status
   */
  static getStatusColor(status: string): string {
    switch (status) {
      case 'success':
        return '#4caf50'; // green
      case 'error':
        return '#f44336'; // red
      case 'running':
        return '#ff9800'; // orange
      case 'idle':
      default:
        return '#9e9e9e'; // gray
    }
  }

  /**
   * Get color for system health status
   */
  static getHealthStatusColor(status: string): string {
    switch (status) {
      case 'healthy':
        return '#4caf50'; // green
      case 'degraded':
        return '#ff9800'; // orange
      case 'unhealthy':
        return '#f44336'; // red
      default:
        return '#9e9e9e'; // gray
    }
  }
}

// Export individual functions for convenience
export const {
  scheduleOrchestration,
  getCoverage,
  getAvailability,
  getSystemHealth,
  getSystemMetrics,
  formatDateForApi,
  getCurrentWeekRange,
  getNextWeekRange,
  getCustomDateRange,
  validateScheduleRequest,
  getOrchestrationSummary,
  getCoverageSummary,
  formatDuration,
  getStatusColor,
  getHealthStatusColor,
} = OrchestratorService;
