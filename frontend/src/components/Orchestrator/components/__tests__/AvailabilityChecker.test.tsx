import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { renderWithProviders } from '../../../../test/utils';
import AvailabilityChecker from '../AvailabilityChecker';
import type { UseOrchestratorReturn } from '../../../../hooks/useOrchestrator';

// Mock the useOrchestrator hook
const defaultMockHook: UseOrchestratorReturn = {
  state: {
    schedules: [],
    currentSchedule: null,
    coverage: {},
    fairnessScores: {},
    assignments: [],
    shifts: [],
    shiftTypes: [],
    employees: [],
    departments: [],
    constraints: [],
    patterns: [],
    incidents: [],
    availabilityData: [],
    overrides: [],
    blockedPeriods: [],
    leaveRequests: [],
    approvals: [],
    notifications: [],
    workloadData: {},
    performanceMetrics: {},
    auditLog: [],
    settings: {},
    exportData: null,
    backup: null,
    templates: [],
    validationResults: {},
    optimizationHistory: [],
    userPreferences: {},
    systemHealth: {
      status: 'healthy',
      lastCheck: new Date().toISOString(),
      issues: []
    },
    loading: {
      schedules: false,
      coverage: false,
      assignments: false,
      shifts: false,
      employees: false,
      departments: false,
      constraints: false,
      patterns: false,
      incidents: false,
      availability: false,
      overrides: false,
      blocked: false,
      leave: false,
      approvals: false,
      notifications: false,
      workload: false,
      performance: false,
      audit: false,
      settings: false,
      export: false,
      backup: false,
      templates: false,
      validation: false,
      optimization: false,
      preferences: false,
      health: false
    },
    error: {
      schedules: null,
      coverage: null,
      assignments: null,
      shifts: null,
      employees: null,
      departments: null,
      constraints: null,
      patterns: null,
      incidents: null,
      availability: null,
      overrides: null,
      blocked: null,
      leave: null,
      approvals: null,
      notifications: null,
      workload: null,
      performance: null,
      audit: null,
      settings: null,
      export: null,
      backup: null,
      templates: null,
      validation: null,
      optimization: null,
      preferences: null,
      health: null
    }
  },
  getAvailabilityForCurrentWeek: jest.fn(),
  getAvailability: jest.fn(),
  createSchedule: jest.fn(),
  updateSchedule: jest.fn(),
  deleteSchedule: jest.fn(),
  generateSchedule: jest.fn(),
  publishSchedule: jest.fn(),
  getCoverageAnalysis: jest.fn(),
  updateCoverageRequirements: jest.fn(),
  optimizeCoverage: jest.fn(),
  createAssignment: jest.fn(),
  updateAssignment: jest.fn(),
  deleteAssignment: jest.fn(),
  bulkAssignShifts: jest.fn(),
  swapAssignments: jest.fn(),
  createShift: jest.fn(),
  updateShift: jest.fn(),
  deleteShift: jest.fn(),
  bulkCreateShifts: jest.fn(),
  createEmployee: jest.fn(),
  updateEmployee: jest.fn(),
  deleteEmployee: jest.fn(),
  bulkUpdateEmployees: jest.fn(),
  createDepartment: jest.fn(),
  updateDepartment: jest.fn(),
  deleteDepartment: jest.fn(),
  createConstraint: jest.fn(),
  updateConstraint: jest.fn(),
  deleteConstraint: jest.fn(),
  validateConstraints: jest.fn(),
  createPattern: jest.fn(),
  updatePattern: jest.fn(),
  deletePattern: jest.fn(),
  applyPattern: jest.fn(),
  createIncident: jest.fn(),
  updateIncident: jest.fn(),
  deleteIncident: jest.fn(),
  assignIncidentCoverage: jest.fn(),
  createOverride: jest.fn(),
  updateOverride: jest.fn(),
  deleteOverride: jest.fn(),
  createBlockedPeriod: jest.fn(),
  updateBlockedPeriod: jest.fn(),
  deleteBlockedPeriod: jest.fn(),
  createLeaveRequest: jest.fn(),
  updateLeaveRequest: jest.fn(),
  deleteLeaveRequest: jest.fn(),
  processLeaveRequest: jest.fn(),
  createApproval: jest.fn(),
  updateApproval: jest.fn(),
  deleteApproval: jest.fn(),
  processApproval: jest.fn(),
  markNotificationRead: jest.fn(),
  clearNotifications: jest.fn(),
  getWorkloadAnalysis: jest.fn(),
  updateWorkloadLimits: jest.fn(),
  balanceWorkload: jest.fn(),
  getPerformanceMetrics: jest.fn(),
  generatePerformanceReport: jest.fn(),
  getAuditLog: jest.fn(),
  exportAuditLog: jest.fn(),
  updateSettings: jest.fn(),
  resetSettings: jest.fn(),
  exportData: jest.fn(),
  importData: jest.fn(),
  createBackup: jest.fn(),
  restoreBackup: jest.fn(),
  createTemplate: jest.fn(),
  updateTemplate: jest.fn(),
  deleteTemplate: jest.fn(),
  applyTemplate: jest.fn(),
  validateSchedule: jest.fn(),
  fixValidationErrors: jest.fn(),
  optimizeSchedule: jest.fn(),
  revertOptimization: jest.fn(),
  updatePreferences: jest.fn(),
  resetPreferences: jest.fn(),
  checkSystemHealth: jest.fn(),
  getSystemStatus: jest.fn()
};

jest.mock('../../../../hooks/useOrchestrator', () => ({
  useOrchestrator: () => defaultMockHook
}));

describe('AvailabilityChecker', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the main title and description', () => {
    renderWithProviders(<AvailabilityChecker />);
    
    expect(screen.getByText('Employee Availability')).toBeInTheDocument();
    expect(screen.getByText('Check employee availability for different shift types and time periods')).toBeInTheDocument();
  });

  it('renders quick availability check section', () => {
    renderWithProviders(<AvailabilityChecker />);
    
    expect(screen.getByText('Quick Availability Check')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /check current week/i })).toBeInTheDocument();
  });

  it('renders custom availability check section', () => {
    renderWithProviders(<AvailabilityChecker />);
    
    expect(screen.getByText('Custom Availability Check')).toBeInTheDocument();
    expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /check availability/i })).toBeInTheDocument();
  });

  it('calls getAvailabilityForCurrentWeek when Check Current Week button is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AvailabilityChecker />);
    
    const checkButton = screen.getByRole('button', { name: /check current week/i });
    await user.click(checkButton);
    
    expect(defaultMockHook.getAvailabilityForCurrentWeek).toHaveBeenCalledWith(undefined);
  });

  it('shows empty state when no data is available', () => {
    renderWithProviders(<AvailabilityChecker />);
    
    expect(screen.getByText('No availability data available. Use the check buttons above to load employee availability.')).toBeInTheDocument();
  });
});
