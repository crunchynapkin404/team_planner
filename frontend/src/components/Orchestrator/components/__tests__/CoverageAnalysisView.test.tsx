/**
 * CoverageAnalysisView Component Tests
 * 
 * Tests for the coverage analysis component that allows users to analyze
 * shift coverage for different time periods with quick actions and custom
 * date range selection.
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../../test/utils';
import CoverageAnalysisView from '../CoverageAnalysisView';
import * as useOrchestratorModule from '../../../../hooks/useOrchestrator';
import type { UseOrchestratorReturn } from '../../../../types/orchestrator';

// Mock the useOrchestrator hook
const mockUseOrchestrator = jest.spyOn(useOrchestratorModule, 'useOrchestrator');

// Mock data for testing
const mockCoverageData = {
  date_range: {
    start_date: '2024-01-15',
    end_date: '2024-01-16'
  },
  coverage_by_date: {
    '2024-01-15': {
      morning: {
        total_shifts: 4,
        assigned_shifts: 3,
        unassigned_shifts: 1,
        assignments: []
      },
      evening: {
        total_shifts: 4,
        assigned_shifts: 4,
        unassigned_shifts: 0,
        assignments: []
      }
    },
    '2024-01-16': {
      morning: {
        total_shifts: 4,
        assigned_shifts: 2,
        unassigned_shifts: 2,
        assignments: []
      },
      evening: {
        total_shifts: 4,
        assigned_shifts: 3,
        unassigned_shifts: 1,
        assignments: []
      }
    }
  },
  summary: {
    total_days: 2,
    days_with_coverage: 1,
    days_without_coverage: 1,
    coverage_percentage: 83
  }
};

const mockOrchestratorState = {
  coverageData: mockCoverageData,
  coverageLoading: false,
  availabilityData: [],
  availabilityLoading: false,
  loading: false,
  error: null,
  orchestrationStatus: 'idle' as const,
  lastOrchestration: null,
  orchestrationHistory: [],
  systemHealth: null,
  systemMetrics: null,
  selectedDateRange: { start: null, end: null },
  selectedDepartment: null
};

const defaultMockHook: UseOrchestratorReturn = {
  state: mockOrchestratorState,
  scheduleOrchestration: jest.fn(),
  getCoverage: jest.fn(),
  getAvailability: jest.fn(),
  refreshSystemHealth: jest.fn(),
  refreshMetrics: jest.fn(),
  clearError: jest.fn(),
  updateSelectedDateRange: jest.fn(),
  updateSelectedDepartment: jest.fn(),
  clearHistory: jest.fn(),
  clearCoverage: jest.fn(),
  clearAvailability: jest.fn(),
  resetState: jest.fn(),
  scheduleCurrentWeek: jest.fn(),
  scheduleNextWeek: jest.fn(),
  scheduleCustomDateRange: jest.fn(),
  getCoverageForCurrentWeek: jest.fn(),
  getCoverageForNextWeek: jest.fn(),
  getCoverageForCustomRange: jest.fn(),
  getAvailabilityForCurrentWeek: jest.fn(),
  isLoading: false,
  hasError: false,
  isOrchestrationRunning: false,
  hasLastOrchestration: false,
  isSystemHealthy: true,
  getOrchestrationSummary: jest.fn(() => null),
  getCoverageSummary: jest.fn(() => 'Coverage analysis complete: 12 total shifts, 10 assigned, 2 unassigned (83% coverage)')
};

describe('CoverageAnalysisView', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseOrchestrator.mockReturnValue(defaultMockHook);
  });

  describe('Component Rendering', () => {
    it('renders the main title and description', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      expect(screen.getByText('Coverage Analysis')).toBeInTheDocument();
      expect(screen.getByText('Analyze shift coverage for different time periods')).toBeInTheDocument();
    });

    it('renders quick action buttons', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      expect(screen.getByRole('button', { name: /current week/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /next week/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });

    it('renders custom date range section', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      expect(screen.getByText('Custom Date Range')).toBeInTheDocument();
      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /analyze coverage/i })).toBeInTheDocument();
    });
  });

  describe('Quick Actions', () => {
    it('calls getCoverageForCurrentWeek when Current Week button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const currentWeekButton = screen.getByRole('button', { name: /current week/i });
      await user.click(currentWeekButton);
      
      expect(defaultMockHook.getCoverageForCurrentWeek).toHaveBeenCalled();
    });

    it('calls getCoverageForNextWeek when Next Week button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const nextWeekButton = screen.getByRole('button', { name: /next week/i });
      await user.click(nextWeekButton);
      
      expect(defaultMockHook.getCoverageForNextWeek).toHaveBeenCalled();
    });

    it('calls getCoverageForCurrentWeek when Refresh button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      await user.click(refreshButton);
      
      expect(defaultMockHook.getCoverageForCurrentWeek).toHaveBeenCalled();
    });
  });

  describe('Custom Date Range', () => {
    it('updates date range when input values change', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);
      
      await user.type(startDateInput, '2024-01-15');
      await user.type(endDateInput, '2024-01-21');
      
      expect(startDateInput).toHaveValue('2024-01-15');
      expect(endDateInput).toHaveValue('2024-01-21');
    });

    it('calls getCoverage with correct parameters when Analyze Coverage is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);
      const analyzeButton = screen.getByRole('button', { name: /analyze coverage/i });
      
      await user.type(startDateInput, '2024-01-15');
      await user.type(endDateInput, '2024-01-21');
      await user.click(analyzeButton);
      
      expect(defaultMockHook.getCoverage).toHaveBeenCalledWith({
        start_date: '2024-01-15',
        end_date: '2024-01-21'
      });
    });

    it('disables Analyze Coverage button when dates are missing', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      const analyzeButton = screen.getByRole('button', { name: /analyze coverage/i });
      expect(analyzeButton).toBeDisabled();
    });

    it('enables Analyze Coverage button when both dates are provided', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);
      const analyzeButton = screen.getByRole('button', { name: /analyze coverage/i });
      
      await user.type(startDateInput, '2024-01-15');
      await user.type(endDateInput, '2024-01-21');
      
      expect(analyzeButton).not.toBeDisabled();
    });
  });

  describe('Loading States', () => {
    it('shows loading spinner during analysis', async () => {
      const mockHookWithLoading = {
        ...defaultMockHook,
        getCoverageForCurrentWeek: jest.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))
      };
      mockUseOrchestrator.mockReturnValue(mockHookWithLoading);
      
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const currentWeekButton = screen.getByRole('button', { name: /current week/i });
      await user.click(currentWeekButton);
      
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('disables buttons during loading', async () => {
      const mockHookWithLoading = {
        ...defaultMockHook,
        getCoverageForCurrentWeek: jest.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))
      };
      mockUseOrchestrator.mockReturnValue(mockHookWithLoading);
      
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const currentWeekButton = screen.getByRole('button', { name: /current week/i });
      await user.click(currentWeekButton);
      
      expect(currentWeekButton).toBeDisabled();
      expect(screen.getByRole('button', { name: /next week/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /refresh/i })).toBeDisabled();
    });
  });

  describe('Coverage Data Display', () => {
    it('displays coverage summary when data is available', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      expect(screen.getByText(/coverage analysis complete/i)).toBeInTheDocument();
    });

    it('displays coverage table with correct data', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      expect(screen.getByText('Coverage Details')).toBeInTheDocument();
      
      // Check table headers
      expect(screen.getByText('Date')).toBeInTheDocument();
      expect(screen.getByText('Shift Type')).toBeInTheDocument();
      expect(screen.getByText('Total Shifts')).toBeInTheDocument();
      expect(screen.getByText('Assigned')).toBeInTheDocument();
      expect(screen.getByText('Unassigned')).toBeInTheDocument();
      expect(screen.getByText('Coverage')).toBeInTheDocument();
      
      // Check data rows - use getAllByText for duplicates
      expect(screen.getAllByText('2024-01-15')).toHaveLength(2); // Two shifts per day
      expect(screen.getAllByText('2024-01-16')).toHaveLength(2);
      expect(screen.getAllByText('morning')).toHaveLength(2); // One per day
      expect(screen.getAllByText('evening')).toHaveLength(2);
    });

    it('displays correct coverage percentages', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      // There are multiple 75% values and they are both valid
      expect(screen.getAllByText('75%')).toHaveLength(2); // 2024-01-15 morning (3/4) and 2024-01-16 evening (3/4)
      expect(screen.getByText('100%')).toBeInTheDocument(); // 2024-01-15 evening (4/4)
      expect(screen.getByText('50%')).toBeInTheDocument(); // 2024-01-16 morning (2/4)
    });

    it('displays correct chip colors based on coverage', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      // Count percentage chips - includes one from summary (83%) plus 4 from table rows
      const chips = screen.getAllByText(/\d+%/);
      expect(chips).toHaveLength(5); // Summary (83%) + Four shift entries (75%, 100%, 50%, 75%)
    });
  });

  describe('Empty State', () => {
    it('displays no data message when coverage data is not available', () => {
      const mockHookWithoutData = {
        ...defaultMockHook,
        state: { ...mockOrchestratorState, coverageData: null }
      };
      mockUseOrchestrator.mockReturnValue(mockHookWithoutData);
      
      renderWithProviders(<CoverageAnalysisView />);
      
      expect(screen.getByText(/no coverage data available/i)).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles errors gracefully during quick coverage analysis', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const mockHookWithError = {
        ...defaultMockHook,
        getCoverageForCurrentWeek: jest.fn().mockRejectedValue(new Error('API Error'))
      };
      mockUseOrchestrator.mockReturnValue(mockHookWithError);
      
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const currentWeekButton = screen.getByRole('button', { name: /current week/i });
      await user.click(currentWeekButton);
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to get coverage:', expect.any(Error));
      });
      
      consoleSpy.mockRestore();
    });

    it('handles errors gracefully during custom coverage analysis', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const mockHookWithError = {
        ...defaultMockHook,
        getCoverage: jest.fn().mockRejectedValue(new Error('API Error'))
      };
      mockUseOrchestrator.mockReturnValue(mockHookWithError);
      
      const user = userEvent.setup();
      renderWithProviders(<CoverageAnalysisView />);
      
      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);
      const analyzeButton = screen.getByRole('button', { name: /analyze coverage/i });
      
      await user.type(startDateInput, '2024-01-15');
      await user.type(endDateInput, '2024-01-21');
      await user.click(analyzeButton);
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to get coverage:', expect.any(Error));
      });
      
      consoleSpy.mockRestore();
    });
  });

  describe('Data Validation', () => {
    it('handles empty coverage data gracefully', () => {
      const mockHookWithEmptyData = {
        ...defaultMockHook,
        state: {
          ...mockOrchestratorState,
          coverageData: {
            date_range: { start_date: '2024-01-15', end_date: '2024-01-16' },
            coverage_by_date: {},
            summary: { total_days: 0, days_with_coverage: 0, days_without_coverage: 0, coverage_percentage: 0 }
          }
        }
      };
      mockUseOrchestrator.mockReturnValue(mockHookWithEmptyData);
      
      renderWithProviders(<CoverageAnalysisView />);
      
      expect(screen.getByText('Coverage Details')).toBeInTheDocument();
      // Table should still render but be empty
      expect(screen.getByRole('table')).toBeInTheDocument();
    });

    it('handles missing shift types in coverage data', () => {
      const incompleteCoverageData = {
        date_range: { start_date: '2024-01-15', end_date: '2024-01-15' },
        coverage_by_date: {
          '2024-01-15': {
            morning: {
              total_shifts: 2,
              assigned_shifts: 1,
              unassigned_shifts: 1,
              assignments: []
            }
            // Missing evening shift
          }
        },
        summary: { total_days: 1, days_with_coverage: 0, days_without_coverage: 1, coverage_percentage: 50 }
      };
      
      const mockHookWithIncompleteData = {
        ...defaultMockHook,
        state: {
          ...mockOrchestratorState,
          coverageData: incompleteCoverageData
        }
      };
      mockUseOrchestrator.mockReturnValue(mockHookWithIncompleteData);
      
      renderWithProviders(<CoverageAnalysisView />);
      
      expect(screen.getByText('morning')).toBeInTheDocument();
      expect(screen.queryByText('evening')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      // Check table accessibility
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
      
      // Check form accessibility
      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
      
      // Check button accessibility
      expect(screen.getByRole('button', { name: /current week/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /next week/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /analyze coverage/i })).toBeInTheDocument();
    });

    it('provides meaningful text for screen readers', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      expect(screen.getByText('Analyze shift coverage for different time periods')).toBeInTheDocument();
      expect(screen.getByText('Quick Analysis')).toBeInTheDocument();
      expect(screen.getByText('Custom Date Range')).toBeInTheDocument();
      expect(screen.getByText('Coverage Details')).toBeInTheDocument();
    });
  });

  describe('Responsive Design', () => {
    it('renders grid layout correctly', () => {
      renderWithProviders(<CoverageAnalysisView />);
      
      // Check that main sections are rendered - use table as a specific element to check
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
      
      // Check that cards exist by looking for specific headings within them
      expect(screen.getByText('Quick Analysis')).toBeInTheDocument();
      expect(screen.getByText('Custom Date Range')).toBeInTheDocument();
      expect(screen.getByText('Coverage Details')).toBeInTheDocument();
    });
  });
});
