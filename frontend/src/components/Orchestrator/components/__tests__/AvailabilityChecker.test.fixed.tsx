import { screen } from '@testing-library/react';
import { renderWithProviders } from '../../../../test/utils';
import AvailabilityChecker from '../AvailabilityChecker';
import * as useOrchestratorModule from '../../../../hooks/useOrchestrator';
import type { UseOrchestratorReturn } from '../../../../types/orchestrator';

// Mock the useOrchestrator hook
const mockUseOrchestrator = jest.spyOn(useOrchestratorModule, 'useOrchestrator');

// Simple mock hook that satisfies the interface
const defaultMockHook: UseOrchestratorReturn = {
  state: {
    orchestrationStatus: 'idle' as const,
    lastOrchestration: null,
    orchestrationHistory: [],
    coverageData: null,
    coverageLoading: false,
    availabilityData: [],
    availabilityLoading: false,
    systemHealth: null,
    systemMetrics: null,
    loading: false,
    error: null,
    selectedDateRange: { start: null, end: null },
    selectedDepartment: null
  },
  scheduleOrchestration: jest.fn().mockResolvedValue({
    success: true,
    statistics: { assignments_made: 0, unassigned_shifts: 0, conflicts_detected: 0, warnings: 0 },
    assignments: [],
    conflicts: [],
    warnings: []
  }),
  getCoverage: jest.fn().mockResolvedValue({
    date_range: { start_date: '2024-01-01', end_date: '2024-01-07' },
    coverage_by_date: {},
    summary: { total_days: 0, days_with_coverage: 0, days_without_coverage: 0, coverage_percentage: 0 }
  }),
  getAvailability: jest.fn().mockResolvedValue({
    date_range: { start_date: '2024-01-01', end_date: '2024-01-07' },
    availability_by_date: {},
    summary: { total_employees: 0, available_employees: 0, unavailable_employees: 0 }
  }),
  refreshSystemHealth: jest.fn().mockResolvedValue({
    status: 'healthy' as const,
    timestamp: '2024-01-01T00:00:00Z',
    version: '1.0.0',
    components: {
      database: 'healthy' as const,
      orchestrator: 'healthy' as const,
      cache: 'healthy' as const,
    }
  }),
  refreshMetrics: jest.fn().mockResolvedValue({
    total_active_employees: 10,
    total_shifts_last_30_days: 100,
    assigned_shifts_last_30_days: 90,
    assignment_rate_percentage: 90,
    unassigned_shifts_last_30_days: 10,
    average_orchestration_time_seconds: 1.5,
    timestamp: '2024-01-01T00:00:00Z'
  }),
  clearError: jest.fn(),
  updateSelectedDateRange: jest.fn(),
  updateSelectedDepartment: jest.fn(),
  clearHistory: jest.fn(),
  clearCoverage: jest.fn(),
  clearAvailability: jest.fn(),
  resetState: jest.fn(),
  scheduleCurrentWeek: jest.fn().mockResolvedValue({
    success: true,
    statistics: { assignments_made: 0, unassigned_shifts: 0, conflicts_detected: 0, warnings: 0 },
    assignments: [],
    conflicts: [],
    warnings: []
  }),
  scheduleNextWeek: jest.fn().mockResolvedValue({
    success: true,
    statistics: { assignments_made: 0, unassigned_shifts: 0, conflicts_detected: 0, warnings: 0 },
    assignments: [],
    conflicts: [],
    warnings: []
  }),
  scheduleCustomDateRange: jest.fn().mockResolvedValue({
    success: true,
    statistics: { assignments_made: 0, unassigned_shifts: 0, conflicts_detected: 0, warnings: 0 },
    assignments: [],
    conflicts: [],
    warnings: []
  }),
  getCoverageForCurrentWeek: jest.fn().mockResolvedValue({
    date_range: { start_date: '2024-01-01', end_date: '2024-01-07' },
    coverage_by_date: {},
    summary: { total_days: 0, days_with_coverage: 0, days_without_coverage: 0, coverage_percentage: 0 }
  }),
  getCoverageForNextWeek: jest.fn().mockResolvedValue({
    date_range: { start_date: '2024-01-08', end_date: '2024-01-14' },
    coverage_by_date: {},
    summary: { total_days: 0, days_with_coverage: 0, days_without_coverage: 0, coverage_percentage: 0 }
  }),
  getCoverageForCustomRange: jest.fn().mockResolvedValue({
    date_range: { start_date: '2024-01-01', end_date: '2024-01-07' },
    coverage_by_date: {},
    summary: { total_days: 0, days_with_coverage: 0, days_without_coverage: 0, coverage_percentage: 0 }
  }),
  getAvailabilityForCurrentWeek: jest.fn().mockResolvedValue({
    date_range: { start_date: '2024-01-01', end_date: '2024-01-07' },
    availability_by_date: {},
    summary: { total_employees: 0, available_employees: 0, unavailable_employees: 0 }
  }),
  isLoading: false,
  hasError: false,
  isOrchestrationRunning: false,
  hasLastOrchestration: false,
  isSystemHealthy: true,
  getOrchestrationSummary: jest.fn(() => null),
  getCoverageSummary: jest.fn(() => null)
};

describe('AvailabilityChecker', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseOrchestrator.mockReturnValue(defaultMockHook);
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
});
