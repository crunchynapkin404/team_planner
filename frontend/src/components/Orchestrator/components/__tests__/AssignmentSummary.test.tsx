import { screen, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import { renderWithProviders } from '../../../../test/utils';
import AssignmentSummary from '../AssignmentSummary';

// Mock the useOrchestrator hook
const defaultMockHook: any = {
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
      timestamp: new Date('2024-01-15T10:30:00Z').toISOString(),
      issues: []
    },
    systemMetrics: {
      total_active_employees: 25,
      unassigned_shifts_last_30_days: 3,
      assignment_rate_percentage: 94.5,
      last_updated: new Date('2024-01-15T10:30:00Z').toISOString()
    },
    lastOrchestration: null,
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
  refreshSystemHealth: jest.fn()
};

jest.mock('../../../../hooks/useOrchestrator', () => ({
  useOrchestrator: () => defaultMockHook
}));

describe('AssignmentSummary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the main title and description', () => {
    renderWithProviders(<AssignmentSummary />);
    
    expect(screen.getByText('Assignment Summary')).toBeInTheDocument();
    expect(screen.getByText('View orchestration results, current assignments, and system summary')).toBeInTheDocument();
  });

  it('renders system summary section', () => {
    renderWithProviders(<AssignmentSummary />);
    
    expect(screen.getByText('System Summary')).toBeInTheDocument();
    expect(screen.getByText('System Health')).toBeInTheDocument();
    expect(screen.getByText('Active Employees')).toBeInTheDocument();
    expect(screen.getByText('Unassigned Shifts')).toBeInTheDocument();
    expect(screen.getByText('Assignment Rate')).toBeInTheDocument();
  });

  it('displays system metrics correctly', () => {
    renderWithProviders(<AssignmentSummary />);
    
    expect(screen.getByText('✓')).toBeInTheDocument(); // System health check mark
    expect(screen.getByText('25')).toBeInTheDocument(); // Active employees
    expect(screen.getByText('3')).toBeInTheDocument(); // Unassigned shifts
    expect(screen.getByText('94.5%')).toBeInTheDocument(); // Assignment rate
  });

  it('shows no orchestration message when no results available', () => {
    renderWithProviders(<AssignmentSummary />);
    
    expect(screen.getByText('No recent orchestration results available.')).toBeInTheDocument();
    expect(screen.getByText('Run a schedule orchestration to see results here.')).toBeInTheDocument();
  });

  it('calls refreshSystemHealth on component mount', async () => {
    renderWithProviders(<AssignmentSummary />);
    
    await waitFor(() => {
      expect(defaultMockHook.refreshSystemHealth).toHaveBeenCalledTimes(1);
    });
  });

  it('displays last health check timestamp', () => {
    renderWithProviders(<AssignmentSummary />);
    
    expect(screen.getByText('Last Health Check')).toBeInTheDocument();
    expect(screen.getByText(/Jan.*15.*2024/)).toBeInTheDocument();
  });
});
