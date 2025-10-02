/**
 * Service for managing recurring shift patterns.
 */

import { apiClient } from './apiClient';

export interface RecurringPattern {
  id: number;
  name: string;
  description: string;
  template: {
    id: number;
    name: string;
    shift_type: string;
  };
  start_time: string;
  end_time: string;
  recurrence_type: 'daily' | 'weekly' | 'biweekly' | 'monthly';
  weekdays: number[]; // 0=Monday, 6=Sunday
  day_of_month: number | null;
  pattern_start_date: string;
  pattern_end_date: string | null;
  assigned_employee: {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
  } | null;
  team: {
    id: number;
    name: string;
  } | null;
  is_active: boolean;
  last_generated_date: string | null;
  created_by: {
    id: number;
    username: string;
  } | null;
  created: string;
}

export interface RecurringPatternCreate {
  name: string;
  description?: string;
  template_id: number;
  start_time: string; // HH:MM format
  end_time: string; // HH:MM format
  recurrence_type: 'daily' | 'weekly' | 'biweekly' | 'monthly';
  weekdays?: number[];
  day_of_month?: number;
  pattern_start_date: string; // YYYY-MM-DD
  pattern_end_date?: string; // YYYY-MM-DD
  assigned_employee_id?: number;
  team_id?: number;
  is_active?: boolean;
}

export interface PatternPreview {
  pattern_name: string;
  preview_days: number;
  dates: string[];
  count: number;
}

export interface GenerateResult {
  message: string;
  shifts_created: number;
  pattern_id: number;
  pattern_name: string;
}

export interface BulkGenerateResult {
  message: string;
  patterns_processed: number;
  total_shifts_created: number;
  results: Array<{
    pattern_id: number;
    pattern_name: string;
    shifts_created: number;
    success: boolean;
    error?: string;
  }>;
}

export const recurringPatternService = {
  /**
   * List all recurring patterns with optional filters.
   */
  async listPatterns(filters?: {
    team?: number;
    employee?: number;
    is_active?: boolean;
  }): Promise<RecurringPattern[]> {
    const params = new URLSearchParams();
    
    if (filters?.team) params.append('team', filters.team.toString());
    if (filters?.employee) params.append('employee', filters.employee.toString());
    if (filters?.is_active !== undefined) params.append('is_active', filters.is_active.toString());
    
    const queryString = params.toString();
    const url = queryString ? `/patterns/?${queryString}` : '/patterns/';
    
    const response: any = await apiClient.get(url);
    return Array.isArray(response) ? response : (response?.results || response || []);
  },

  /**
   * Get a single recurring pattern by ID.
   */
  async getPattern(id: number): Promise<RecurringPattern> {
    const response: any = await apiClient.get(`/patterns/${id}/`);
    return response;
  },

  /**
   * Create a new recurring pattern.
   */
  async createPattern(data: RecurringPatternCreate): Promise<{ id: number; message: string }> {
    const response: any = await apiClient.post('/patterns/', data);
    return response;
  },

  /**
   * Update an existing recurring pattern.
   */
  async updatePattern(id: number, data: Partial<RecurringPatternCreate>): Promise<{ message: string }> {
    const response: any = await apiClient.put(`/patterns/${id}/`, data);
    return response;
  },

  /**
   * Delete a recurring pattern.
   */
  async deletePattern(id: number): Promise<void> {
    await apiClient.delete(`/patterns/${id}/`);
  },

  /**
   * Generate shifts from a pattern up to a specified number of days ahead.
   */
  async generateShifts(id: number, daysAhead: number = 30): Promise<GenerateResult> {
    const response: any = await apiClient.post(`/patterns/${id}/generate/`, {
      days_ahead: daysAhead,
    });
    return response;
  },

  /**
   * Preview dates that would be generated for a pattern.
   */
  async previewPattern(id: number, previewDays: number = 30): Promise<PatternPreview> {
    const response: any = await apiClient.post(`/patterns/${id}/preview/`, {
      preview_days: previewDays,
    });
    return response;
  },

  /**
   * Bulk generate shifts for all active patterns.
   */
  async bulkGenerate(daysAhead: number = 14): Promise<BulkGenerateResult> {
    const response: any = await apiClient.post('/patterns/bulk-generate/', {
      days_ahead: daysAhead,
    });
    return response;
  },
};

export default recurringPatternService;
