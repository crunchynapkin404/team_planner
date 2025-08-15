import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../../test/utils';
import OrchestratorStatusPanel from '../OrchestratorStatusPanel';

// Mock the orchestrator service
jest.mock('../../../../services/orchestratorService', () => ({
  OrchestratorService: {
    formatDuration: jest.fn((seconds) => `${seconds}s`),
  },
}));

// Mock the hooks
jest.mock('../../../../hooks/useOrchestrator', () => ({
  useOrchestrator: jest.fn(),
  useOrchestratorStatus: jest.fn(),
}));

const mockUseOrchestrator = require('../../../../hooks/useOrchestrator').useOrchestrator;
const mockUseOrchestratorStatus = require('../../../../hooks/useOrchestrator').useOrchestratorStatus;

describe('OrchestratorStatusPanel', () => {
  const mockRefreshSystemHealth = jest.fn();
  const mockRefreshMetrics = jest.fn();

  const defaultOrchestratorState = {
    systemMetrics: {
      assignment_rate_percentage: 85.5,
      average_orchestration_time_seconds: 120,
      total_shifts_last_30_days: 1234,
      total_active_employees: 25,
      unassigned_shifts_last_30_days: 5,
    },
  };

  const defaultSystemHealth = {
    status: 'healthy',
    timestamp: '2024-01-15T10:30:00Z',
    response_time_ms: 150,
    version: '2.1.0',
    components: {
      database: 'healthy',
      cache: 'healthy',
      orchestrator: 'healthy',
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockUseOrchestrator.mockReturnValue({
      refreshSystemHealth: mockRefreshSystemHealth,
      refreshMetrics: mockRefreshMetrics,
      state: defaultOrchestratorState,
    });

    mockUseOrchestratorStatus.mockReturnValue({
      systemHealth: defaultSystemHealth,
      isSystemHealthy: true,
    });
  });

  describe('Component Rendering', () => {
    it('renders all main sections correctly', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      // Check main heading
      expect(screen.getByText('System Status')).toBeInTheDocument();

      // Check main cards
      expect(screen.getByText('Overall Health')).toBeInTheDocument();
      expect(screen.getByText('Components')).toBeInTheDocument();
      expect(screen.getByText('Performance')).toBeInTheDocument();
      expect(screen.getByText('System Information')).toBeInTheDocument();

      // Check refresh button
      expect(screen.getByRole('button', { name: /refresh status/i })).toBeInTheDocument();
    });

    it('displays overall health status correctly', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('HEALTHY')).toBeInTheDocument();
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
      expect(screen.getByText(/Response time: 150ms/)).toBeInTheDocument();
    });

    it('displays component status correctly', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      // Check component statuses
      expect(screen.getByText('database')).toBeInTheDocument();
      expect(screen.getByText('cache')).toBeInTheDocument();
      expect(screen.getByText('orchestrator')).toBeInTheDocument();
      
      // Check all components show healthy status
      const healthyStatuses = screen.getAllByText('healthy');
      expect(healthyStatuses).toHaveLength(3); // 3 components (no overall status chip text)
    });

    it('displays performance metrics correctly', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('Assignment Rate (30d)')).toBeInTheDocument();
      expect(screen.getByText('85.5%')).toBeInTheDocument();
      expect(screen.getByText('Avg. Orchestration Time')).toBeInTheDocument();
      expect(screen.getByText('120s')).toBeInTheDocument();
      expect(screen.getByText('Total Shifts (30d)')).toBeInTheDocument();
      expect(screen.getByText('1,234')).toBeInTheDocument();
    });

    it('displays system information correctly', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('Version')).toBeInTheDocument();
      expect(screen.getByText('2.1.0')).toBeInTheDocument();
      expect(screen.getByText('Active Employees')).toBeInTheDocument();
      expect(screen.getByText('25')).toBeInTheDocument();
      expect(screen.getByText('Unassigned Shifts (30d)')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('Operational')).toBeInTheDocument();
    });
  });

  describe('Health Status States', () => {
    it('displays healthy status correctly', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('HEALTHY')).toBeInTheDocument();
      expect(screen.getByText('Operational')).toBeInTheDocument();
      
      // Check for success icon (CheckCircle) - multiple icons expected
      expect(screen.getAllByTestId('CheckCircleIcon').length).toBeGreaterThan(0);
    });

    it('displays degraded status correctly', () => {
      mockUseOrchestratorStatus.mockReturnValue({
        systemHealth: {
          ...defaultSystemHealth,
          status: 'degraded',
        },
        isSystemHealthy: false,
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('DEGRADED')).toBeInTheDocument();
      expect(screen.getByText('Issues Detected')).toBeInTheDocument();
      
      // Check for warning icon
      expect(screen.getByTestId('WarningIcon')).toBeInTheDocument();
    });

    it('displays unhealthy status correctly', () => {
      mockUseOrchestratorStatus.mockReturnValue({
        systemHealth: {
          ...defaultSystemHealth,
          status: 'unhealthy',
        },
        isSystemHealthy: false,
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('UNHEALTHY')).toBeInTheDocument();
      expect(screen.getByText('Issues Detected')).toBeInTheDocument();
      
      // Check for error icon
      expect(screen.getByTestId('ErrorIcon')).toBeInTheDocument();
    });

    it('displays unknown status correctly', () => {
      mockUseOrchestratorStatus.mockReturnValue({
        systemHealth: {
          ...defaultSystemHealth,
          status: 'unknown',
        },
        isSystemHealthy: false,
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
      expect(screen.getByText('Issues Detected')).toBeInTheDocument();
    });
  });

  describe('Component Status Display', () => {
    it('handles mixed component statuses', () => {
      mockUseOrchestratorStatus.mockReturnValue({
        systemHealth: {
          ...defaultSystemHealth,
          components: {
            database: 'healthy',
            cache: 'degraded',
            orchestrator: 'unhealthy',
          },
        },
        isSystemHealthy: false,
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('database')).toBeInTheDocument();
      expect(screen.getByText('cache')).toBeInTheDocument();
      expect(screen.getByText('orchestrator')).toBeInTheDocument();
      
      // Check individual statuses
      expect(screen.getByText('degraded')).toBeInTheDocument();
      expect(screen.getByText('unhealthy')).toBeInTheDocument();
    });

    it('handles missing component data', () => {
      mockUseOrchestratorStatus.mockReturnValue({
        systemHealth: {
          ...defaultSystemHealth,
          components: undefined,
        },
        isSystemHealthy: true,
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('No component data available')).toBeInTheDocument();
    });
  });

  describe('Performance Metrics Display', () => {
    it('handles missing performance data', () => {
      mockUseOrchestrator.mockReturnValue({
        refreshSystemHealth: mockRefreshSystemHealth,
        refreshMetrics: mockRefreshMetrics,
        state: { systemMetrics: null },
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('No performance data available')).toBeInTheDocument();
    });

    it('handles missing individual metrics', () => {
      mockUseOrchestrator.mockReturnValue({
        refreshSystemHealth: mockRefreshSystemHealth,
        refreshMetrics: mockRefreshMetrics,
        state: {
          systemMetrics: {
            assignment_rate_percentage: 75.0,
            // Missing other fields
          },
        },
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('75.0%')).toBeInTheDocument();
      expect(screen.getAllByText('N/A')).toHaveLength(4); // For missing metrics (system info also has N/A)
    });

    it('formats large numbers correctly', () => {
      mockUseOrchestrator.mockReturnValue({
        refreshSystemHealth: mockRefreshSystemHealth,
        refreshMetrics: mockRefreshMetrics,
        state: {
          systemMetrics: {
            ...defaultOrchestratorState.systemMetrics,
            total_shifts_last_30_days: 5678901,
          },
        },
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('5,678,901')).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('calls refresh functions when refresh button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<OrchestratorStatusPanel />);

      const refreshButton = screen.getByRole('button', { name: /refresh status/i });
      await user.click(refreshButton);

      expect(mockRefreshSystemHealth).toHaveBeenCalledTimes(1);
      expect(mockRefreshMetrics).toHaveBeenCalledTimes(1);
    });

    it('handles refresh errors gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      mockRefreshSystemHealth.mockRejectedValue(new Error('Refresh failed'));
      
      const user = userEvent.setup();
      renderWithProviders(<OrchestratorStatusPanel />);

      const refreshButton = screen.getByRole('button', { name: /refresh status/i });
      await user.click(refreshButton);

      expect(consoleSpy).toHaveBeenCalledWith('Failed to refresh status:', expect.any(Error));
      
      consoleSpy.mockRestore();
    });
  });

  describe('Data Formatting', () => {
    it('formats timestamps correctly', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      // Check that timestamp is formatted (exact format depends on locale)
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });

    it('handles missing timestamps', () => {
      mockUseOrchestratorStatus.mockReturnValue({
        systemHealth: {
          ...defaultSystemHealth,
          timestamp: undefined,
        },
        isSystemHealthy: true,
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('Last updated: Unknown')).toBeInTheDocument();
    });

    it('handles missing system health data', () => {
      mockUseOrchestratorStatus.mockReturnValue({
        systemHealth: null,
        isSystemHealthy: false,
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
      expect(screen.getByText('Last updated: Unknown')).toBeInTheDocument();
      expect(screen.getByText('Unknown')).toBeInTheDocument(); // Version
    });
  });

  describe('Progress Bar Display', () => {
    it('displays assignment rate progress bar correctly', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveAttribute('aria-valuenow', '86'); // Material UI rounds to nearest integer
    });

    it('handles zero assignment rate', () => {
      mockUseOrchestrator.mockReturnValue({
        refreshSystemHealth: mockRefreshSystemHealth,
        refreshMetrics: mockRefreshMetrics,
        state: {
          systemMetrics: {
            ...defaultOrchestratorState.systemMetrics,
            assignment_rate_percentage: 0,
          },
        },
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '0');
      expect(screen.getByText('0.0%')).toBeInTheDocument();
    });

    it('handles 100% assignment rate', () => {
      mockUseOrchestrator.mockReturnValue({
        refreshSystemHealth: mockRefreshSystemHealth,
        refreshMetrics: mockRefreshMetrics,
        state: {
          systemMetrics: {
            ...defaultOrchestratorState.systemMetrics,
            assignment_rate_percentage: 100,
          },
        },
      });

      renderWithProviders(<OrchestratorStatusPanel />);

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '100');
      expect(screen.getByText('100.0%')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      // Check button has accessible name
      expect(screen.getByRole('button', { name: /refresh status/i })).toBeInTheDocument();
      
      // Check progress bar has proper role
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('provides meaningful tooltip for refresh button', async () => {
      const user = userEvent.setup();
      renderWithProviders(<OrchestratorStatusPanel />);

      const refreshButton = screen.getByRole('button', { name: /refresh status/i });
      
      // Hover to show tooltip
      await user.hover(refreshButton);
      
      await waitFor(() => {
        expect(screen.getByText('Refresh status')).toBeInTheDocument();
      });
    });

    it('uses semantic markup for status information', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      // Check for proper heading hierarchy
      expect(screen.getByRole('heading', { name: /system status/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /overall health/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /components/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /performance/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /system information/i })).toBeInTheDocument();
    });
  });

  describe('Responsive Design', () => {
    it('renders grid layout correctly', () => {
      renderWithProviders(<OrchestratorStatusPanel />);

      // Check that main grid container exists
      const gridContainers = screen.getAllByRole('generic');
      expect(gridContainers.length).toBeGreaterThan(0);
    });
  });
});
