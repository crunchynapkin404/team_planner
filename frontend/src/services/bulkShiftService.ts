/**
 * Bulk shift operations service
 * 
 * Provides methods for:
 * - Bulk creating shifts from templates
 * - Bulk assigning employees to shifts
 * - Bulk modifying shift times
 * - Bulk deleting shifts
 * - CSV import/export
 */

import { apiClient } from './apiClient';

// Types
export interface BulkCreateRequest {
  template_id: number;
  start_date: string; // YYYY-MM-DD
  end_date: string;   // YYYY-MM-DD
  employee_ids: number[];
  start_time?: string; // HH:MM:SS
  end_time?: string;   // HH:MM:SS
  rotation_strategy?: 'sequential' | 'distribute';
  dry_run?: boolean;
}

export interface BulkCreateResult {
  template_name: string;
  date_range: string;
  total_days: number;
  shifts_to_create: number;
  conflicts: number;
  conflict_details: ConflictDetail[];
  created: number;
}

export interface ConflictDetail {
  date?: string;
  shift_id?: number;
  employee?: string;
  employee_id?: number;
  reason: string;
  old_time?: string;
  new_time?: string;
  status?: string;
  time?: string;
}

export interface BulkAssignRequest {
  shift_ids: number[];
  employee_id: number;
  dry_run?: boolean;
}

export interface BulkAssignResult {
  employee: string;
  employee_id: number;
  total_shifts: number;
  shifts_to_update: number;
  conflicts: number;
  conflict_details: ConflictDetail[];
  updated: number;
}

export interface BulkModifyTimesRequest {
  shift_ids: number[];
  new_start_time?: string; // HH:MM:SS
  new_end_time?: string;   // HH:MM:SS
  time_offset_minutes?: number;
  dry_run?: boolean;
}

export interface BulkModifyTimesResult {
  total_shifts: number;
  shifts_to_update: number;
  conflicts: number;
  conflict_details: ConflictDetail[];
  updated: number;
}

export interface BulkDeleteRequest {
  shift_ids: number[];
  force?: boolean;
  dry_run?: boolean;
}

export interface BulkDeleteResult {
  total_shifts: number;
  shifts_to_delete: number;
  warnings: number;
  warning_details: ConflictDetail[];
  deleted: number;
}

export interface ImportResult {
  total_rows: number;
  valid_shifts: number;
  errors: number;
  error_details: Array<{
    row: number;
    error: string;
  }>;
  created: number;
}

class BulkShiftService {
  /**
   * Bulk create shifts from a template over a date range
   */
  async bulkCreateShifts(data: BulkCreateRequest): Promise<BulkCreateResult> {
    const response = await apiClient.post<BulkCreateResult>('/api/shifts/bulk-create/', data);
    return response as BulkCreateResult;
  }

  /**
   * Bulk assign an employee to multiple shifts
   */
  async bulkAssignEmployees(data: BulkAssignRequest): Promise<BulkAssignResult> {
    const response = await apiClient.post<BulkAssignResult>('/api/shifts/bulk-assign/', data);
    return response as BulkAssignResult;
  }

  /**
   * Bulk modify shift times
   */
  async bulkModifyTimes(data: BulkModifyTimesRequest): Promise<BulkModifyTimesResult> {
    const response = await apiClient.post<BulkModifyTimesResult>('/api/shifts/bulk-modify-times/', data);
    return response as BulkModifyTimesResult;
  }

  /**
   * Bulk delete shifts
   */
  async bulkDeleteShifts(data: BulkDeleteRequest): Promise<BulkDeleteResult> {
    const response = await apiClient.post<BulkDeleteResult>('/api/shifts/bulk-delete/', data);
    return response as BulkDeleteResult;
  }

  /**
   * Export shifts to CSV
   */
  async exportShiftsCSV(shiftIds: number[]): Promise<Blob> {
    const response = await apiClient.post<Blob>(
      '/api/shifts/export-csv/',
      { shift_ids: shiftIds },
      { responseType: 'blob' }
    );
    return response as Blob;
  }

  /**
   * Import shifts from CSV
   */
  async importShiftsCSV(csvContent: string, dryRun: boolean = false): Promise<ImportResult> {
    const response = await apiClient.post<ImportResult>('/api/shifts/import-csv/', {
      csv_content: csvContent,
      dry_run: dryRun,
    });
    return response as ImportResult;
  }

  /**
   * Import shifts from CSV file
   */
  async importShiftsCSVFile(file: File, dryRun: boolean = false): Promise<ImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('dry_run', dryRun.toString());

    const response = await apiClient.post<ImportResult>('/api/shifts/import-csv/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response as ImportResult;
  }

  /**
   * Download CSV blob as file
   */
  downloadCSV(blob: Blob, filename: string = 'shifts_export.csv'): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }
}

export default new BulkShiftService();
