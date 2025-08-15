/**
 * Stage 3: API Integration Testing
 * 
 * Tests for OrchestratorService API integration using mocked apiClient
 * Covers all orchestrator endpoints, error handling, and integration scenarios
 */

import { OrchestratorService } from '../../services/orchestratorService';
import { apiClient } from '../../services/apiClient';

// Mock the API client
jest.mock('../../services/apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  }
}));

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('OrchestratorService API Integration', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    
    // Clear localStorage before each test
    localStorage.clear();
    // Set up a test token
    localStorage.setItem('token', 'test-token-12345');
  });

  describe('Schedule Orchestration API', () => {
    test('should successfully schedule orchestration with valid data', async () => {
      const requestData = {
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: '1',
        options: {
          dry_run: false,
          force: true
        }
      };

      const mockResponse = {
        success: true,
        statistics: {
          assignments_made: 8,
          unassigned_shifts: 2,
          conflicts_detected: 0,
          warnings: 1
        },
        assignments: [
          {
            assignment_id: 'test-assignment-1',
            shift_id: 1,
            employee_id: 1,
            employee_name: 'John Doe',
            auto_assigned: true,
            shift_type: 'morning',
            start_datetime: '2024-01-15T09:00:00Z',
            end_datetime: '2024-01-15T17:00:00Z'
          }
        ],
        conflicts: [],
        warnings: ['Some shifts may need manual review'],
        execution_time: 12.5
      };

      mockApiClient.post.mockResolvedValue(mockResponse);

      const result = await OrchestratorService.scheduleOrchestration(requestData);

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/orchestrator/schedule/',
        requestData
      );

      expect(result).toMatchObject({
        success: true,
        statistics: {
          assignments_made: 8,
          unassigned_shifts: 2,
          conflicts_detected: 0,
          warnings: 1
        },
        assignments: expect.any(Array),
        conflicts: expect.any(Array),
        warnings: expect.any(Array)
      });

      expect(result.assignments).toHaveLength(1);
      expect(result.assignments[0]).toMatchObject({
        assignment_id: 'test-assignment-1',
        shift_id: 1,
        employee_id: 1,
        employee_name: 'John Doe',
        auto_assigned: true,
        shift_type: 'morning'
      });
    });

    test('should handle API errors gracefully', async () => {
      const requestData = {
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: '1'
      };

      const apiError = {
        message: 'Department not found',
        status: 404,
        data: { detail: 'Department not found' }
      };

      mockApiClient.post.mockRejectedValue(apiError);

      await expect(OrchestratorService.scheduleOrchestration(requestData))
        .rejects
        .toThrow('Failed to schedule orchestration: Department not found');

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/orchestrator/schedule/',
        requestData
      );
    });

    test('should handle validation errors', async () => {
      const requestData = {
        start_date: 'invalid-date',
        end_date: '2024-01-21',
        department_id: '1'
      };

      const validationError = {
        message: 'Invalid date format',
        status: 400,
        data: { 
          detail: 'Invalid date format',
          errors: { start_date: ['Invalid date format'] }
        }
      };

      mockApiClient.post.mockRejectedValue(validationError);

      await expect(OrchestratorService.scheduleOrchestration(requestData))
        .rejects
        .toThrow('Failed to schedule orchestration: Invalid date format');
    });

    test('should handle server errors', async () => {
      const requestData = {
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: '1'
      };

      const serverError = {
        message: 'Internal server error',
        status: 500,
        data: { detail: 'Internal server error' }
      };

      mockApiClient.post.mockRejectedValue(serverError);

      await expect(OrchestratorService.scheduleOrchestration(requestData))
        .rejects
        .toThrow('Failed to schedule orchestration: Internal server error');
    });
  });

  describe('Coverage Analysis API', () => {
    test('should successfully fetch coverage data', async () => {
      const mockResponse = {
        date_range: {
          start_date: '2024-01-15',
          end_date: '2024-01-21'
        },
        coverage_by_date: {
          '2024-01-15': {
            'morning': {
              total_shifts: 5,
              assigned_shifts: 4,
              unassigned_shifts: 1,
              assignments: []
            }
          }
        },
        summary: {
          total_days: 7,
          days_with_coverage: 6,
          days_without_coverage: 1,
          coverage_percentage: 85.7
        }
      };

      mockApiClient.get.mockResolvedValue(mockResponse);

      const result = await OrchestratorService.getCoverage({
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: '1'
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/orchestrator/coverage/', {
        params: {
          start_date: '2024-01-15',
          end_date: '2024-01-21',
          department_id: '1'
        }
      });

      expect(result).toMatchObject({
        date_range: {
          start_date: '2024-01-15',
          end_date: '2024-01-21'
        },
        coverage_by_date: expect.any(Object),
        summary: {
          total_days: 7,
          days_with_coverage: 6,
          days_without_coverage: 1,
          coverage_percentage: 85.7
        }
      });
    });

    test('should handle coverage API errors', async () => {
      const apiError = {
        message: 'Department not found',
        status: 404,
        data: { detail: 'Department not found' }
      };

      mockApiClient.get.mockRejectedValue(apiError);

      await expect(OrchestratorService.getCoverage({
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: '999'
      }))
        .rejects
        .toThrow('Failed to get coverage data: Department not found');
    });
  });

  describe('Availability Analysis API', () => {
    test('should successfully fetch availability data', async () => {
      const mockResponse = {
        time_range: {
          start: '2024-01-15',
          end: '2024-01-21'
        },
        available_employees: [
          {
            employee_id: 1,
            name: 'John Doe',
            email: 'john@example.com',
            available_for_incidents: true,
            available_for_waakdienst: true,
            current_assignments_count: 2,
            fairness_score: 0.8,
            last_assignment_date: '2024-01-10'
          }
        ],
        total_available: 1
      };

      mockApiClient.get.mockResolvedValue(mockResponse);

      const result = await OrchestratorService.getAvailability({
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: '1'
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/orchestrator/availability/', {
        params: {
          start_date: '2024-01-15',
          end_date: '2024-01-21',
          department_id: '1'
        }
      });

      expect(result).toMatchObject({
        time_range: {
          start: '2024-01-15',
          end: '2024-01-21'
        },
        available_employees: expect.any(Array),
        total_available: 1
      });

      expect(result.available_employees[0]).toMatchObject({
        employee_id: 1,
        name: 'John Doe',
        email: 'john@example.com',
        available_for_incidents: true,
        available_for_waakdienst: true
      });
    });

    test('should handle availability API errors', async () => {
      const apiError = {
        message: 'Department not found',
        status: 404,
        data: { detail: 'Department not found' }
      };

      mockApiClient.get.mockRejectedValue(apiError);

      await expect(OrchestratorService.getAvailability({
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: '999'
      }))
        .rejects
        .toThrow('Failed to get availability data: Department not found');
    });
  });

  describe('System Health API', () => {
    test('should successfully fetch system health', async () => {
      const mockResponse = {
        status: 'healthy' as const,
        timestamp: '2024-01-15T10:00:00Z',
        version: '2.0.0',
        components: {
          database: 'healthy' as const,
          orchestrator: 'healthy' as const,
          cache: 'healthy' as const
        },
        response_time_ms: 150
      };

      mockApiClient.get.mockResolvedValue(mockResponse);

      const result = await OrchestratorService.getSystemHealth();

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/orchestrator-status/health/');

      expect(result).toMatchObject({
        status: 'healthy',
        timestamp: '2024-01-15T10:00:00Z',
        version: '2.0.0',
        components: {
          database: 'healthy',
          orchestrator: 'healthy',
          cache: 'healthy'
        },
        response_time_ms: 150
      });
    });

    test('should handle health check errors', async () => {
      const apiError = {
        message: 'Health check failed',
        status: 503,
        data: { detail: 'Service unavailable' }
      };

      mockApiClient.get.mockRejectedValue(apiError);

      await expect(OrchestratorService.getSystemHealth())
        .rejects
        .toThrow('Failed to get system health: Health check failed');
    });
  });

  describe('System Metrics API', () => {
    test('should successfully fetch system metrics', async () => {
      const mockResponse = {
        total_active_employees: 25,
        total_shifts_last_30_days: 300,
        assigned_shifts_last_30_days: 285,
        assignment_rate_percentage: 95.0,
        unassigned_shifts_last_30_days: 15,
        average_orchestration_time_seconds: 12.5,
        timestamp: '2024-01-15T10:00:00Z'
      };

      mockApiClient.get.mockResolvedValue(mockResponse);

      const result = await OrchestratorService.getSystemMetrics();

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/orchestrator-status/metrics/');

      expect(result).toMatchObject({
        total_active_employees: 25,
        total_shifts_last_30_days: 300,
        assigned_shifts_last_30_days: 285,
        assignment_rate_percentage: 95.0,
        unassigned_shifts_last_30_days: 15,
        average_orchestration_time_seconds: 12.5,
        timestamp: '2024-01-15T10:00:00Z'
      });
    });

    test('should handle metrics API errors', async () => {
      const apiError = {
        message: 'Metrics service unavailable',
        status: 503,
        data: { detail: 'Service temporarily unavailable' }
      };

      mockApiClient.get.mockRejectedValue(apiError);

      await expect(OrchestratorService.getSystemMetrics())
        .rejects
        .toThrow('Failed to get system metrics: Metrics service unavailable');
    });
  });

  describe('Request Serialization and Error Handling', () => {
    test('should properly serialize date parameters', async () => {
      const mockResponse = {
        date_range: { start_date: '2024-01-15', end_date: '2024-01-21' },
        coverage_by_date: {},
        summary: { total_days: 7, days_with_coverage: 7, days_without_coverage: 0, coverage_percentage: 100 }
      };

      mockApiClient.get.mockResolvedValue(mockResponse);

      await OrchestratorService.getCoverage({
        start_date: '2024-01-15',
        end_date: '2024-01-21'
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/orchestrator/coverage/', {
        params: {
          start_date: '2024-01-15',
          end_date: '2024-01-21'
        }
      });
    });

    test('should handle network timeout errors', async () => {
      const timeoutError = {
        message: 'Request timeout',
        status: 500,
        data: { detail: 'Request took too long to complete' }
      };

      mockApiClient.post.mockRejectedValue(timeoutError);

      await expect(OrchestratorService.scheduleOrchestration({
        start_date: '2024-01-15',
        end_date: '2024-01-21'
      }))
        .rejects
        .toThrow('Failed to schedule orchestration: Request timeout');
    });

    test('should handle malformed response data', async () => {
      mockApiClient.get.mockResolvedValue(null);

      const result = await OrchestratorService.getSystemHealth();

      expect(result).toBeNull();
    });

    test('should handle authentication errors', async () => {
      const authError = {
        message: 'Authentication required',
        status: 401,
        data: { detail: 'Token invalid or expired' }
      };

      mockApiClient.get.mockRejectedValue(authError);

      await expect(OrchestratorService.getSystemHealth())
        .rejects
        .toThrow('Failed to get system health: Authentication required');
    });
  });

  describe('API Endpoint Validation', () => {
    test('should call correct endpoints with proper parameters', async () => {
      const mockHealthResponse = { status: 'healthy', timestamp: '2024-01-15T10:00:00Z', version: '1.0.0', components: { database: 'healthy', orchestrator: 'healthy', cache: 'healthy' } };
      const mockMetricsResponse = { total_active_employees: 25, total_shifts_last_30_days: 300, assigned_shifts_last_30_days: 285, assignment_rate_percentage: 95.0, unassigned_shifts_last_30_days: 15, average_orchestration_time_seconds: 12.5, timestamp: '2024-01-15T10:00:00Z' };

      mockApiClient.get.mockResolvedValueOnce(mockHealthResponse);
      mockApiClient.get.mockResolvedValueOnce(mockMetricsResponse);

      await OrchestratorService.getSystemHealth();
      await OrchestratorService.getSystemMetrics();

      expect(mockApiClient.get).toHaveBeenNthCalledWith(1, '/api/orchestrator-status/health/');
      expect(mockApiClient.get).toHaveBeenNthCalledWith(2, '/api/orchestrator-status/metrics/');
    });

    test('should pass optional parameters correctly', async () => {
      const mockResponse = {
        time_range: { start: '2024-01-15', end: '2024-01-21' },
        available_employees: [],
        total_available: 0
      };

      mockApiClient.get.mockResolvedValue(mockResponse);

      await OrchestratorService.getAvailability({
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        shift_type: 'incidents',
        department_id: '1'
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/orchestrator/availability/', {
        params: {
          start_date: '2024-01-15',
          end_date: '2024-01-21',
          shift_type: 'incidents',
          department_id: '1'
        }
      });
    });
  });
});
