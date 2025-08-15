import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { jest } from '@jest/globals';
import React from 'react';
import { useOrchestrator, useOrchestratorStatus, useOrchestratorData } from '../useOrchestrator';
import type { OrchestratorState } from '../../types/orchestrator';
import { OrchestratorService } from '../../services/orchestratorService';

// Mock the orchestrator service
jest.mock('../../services/orchestratorService');

// Create a mock reducer for testing
const mockOrchestratorReducer = (
  state: OrchestratorState = {
    orchestrationStatus: 'idle',
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
    selectedDepartment: null,
  },
  action: any
): OrchestratorState => {
  switch (action.type) {
    case 'orchestrator/setError':
      return { ...state, error: null };
    case 'orchestrator/updateDateRange':
      return { ...state, selectedDateRange: action.payload };
    case 'orchestrator/updateDepartment':
      return { ...state, selectedDepartment: action.payload };
    case 'orchestrator/reset':
      return {
        ...state,
        lastOrchestration: null,
        error: null,
        selectedDepartment: null,
      };
    default:
      return state;
  }
};

// Mock the async thunks
const mockScheduleOrchestrationAsync = jest.fn();
const mockGetCoverageAsync = jest.fn();
const mockGetAvailabilityAsync = jest.fn();
const mockGetSystemHealthAsync = jest.fn();
const mockGetSystemMetricsAsync = jest.fn();

jest.mock('../../store/orchestratorSlice', () => ({
  __esModule: true,
  default: mockOrchestratorReducer,
  scheduleOrchestrationAsync: mockScheduleOrchestrationAsync,
  getCoverageAsync: mockGetCoverageAsync,
  getAvailabilityAsync: mockGetAvailabilityAsync,
  getSystemHealthAsync: mockGetSystemHealthAsync,
  getSystemMetricsAsync: mockGetSystemMetricsAsync,
}));

const mockedOrchestratorService = jest.mocked(OrchestratorService);

// Test store setup
const createTestStore = (initialState: Partial<OrchestratorState> = {}) => {
  return configureStore({
    reducer: {
      orchestrator: mockOrchestratorReducer,
    },
    preloadedState: {
      orchestrator: {
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
        selectedDepartment: null,
        ...initialState,
      },
    },
  });
};

// Test wrapper
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(Provider, { store, children });
};

describe('useOrchestrator Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup default mocks
    mockedOrchestratorService.getCurrentWeekRange.mockReturnValue({
      start_date: '2024-01-15',
      end_date: '2024-01-21',
    });
    
    mockedOrchestratorService.getNextWeekRange.mockReturnValue({
      start_date: '2024-01-22',
      end_date: '2024-01-28',
    });
    
    mockedOrchestratorService.getCustomDateRange.mockReturnValue({
      start_date: '2024-01-15',
      end_date: '2024-01-21',
    });
  });

  describe('Basic Hook Functionality', () => {
    it('should return initial state correctly', () => {
      const store = createTestStore();
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.state.orchestrationStatus).toBe('idle');
      expect(result.current.state.lastOrchestration).toBeNull();
      expect(result.current.state.loading).toBe(false);
      expect(result.current.state.error).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.hasError).toBe(false);
      expect(result.current.isOrchestrationRunning).toBe(false);
      expect(result.current.hasLastOrchestration).toBe(false);
    });

    it('should provide all expected functions', () => {
      const store = createTestStore();
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      // Core actions
      expect(typeof result.current.scheduleOrchestration).toBe('function');
      expect(typeof result.current.getCoverage).toBe('function');
      expect(typeof result.current.getAvailability).toBe('function');
      expect(typeof result.current.refreshSystemHealth).toBe('function');
      expect(typeof result.current.refreshMetrics).toBe('function');
      
      // UI actions
      expect(typeof result.current.clearError).toBe('function');
      expect(typeof result.current.updateSelectedDateRange).toBe('function');
      expect(typeof result.current.updateSelectedDepartment).toBe('function');
      
      // Convenience actions
      expect(typeof result.current.scheduleCurrentWeek).toBe('function');
      expect(typeof result.current.scheduleNextWeek).toBe('function');
      expect(typeof result.current.getCoverageForCurrentWeek).toBe('function');
      expect(typeof result.current.getAvailabilityForCurrentWeek).toBe('function');
    });
  });

  describe('Schedule Orchestration', () => {
    it('should call scheduleOrchestration with correct parameters', async () => {
      const store = createTestStore();
      const mockResult = {
        type: 'orchestrator/scheduleOrchestration/fulfilled',
        payload: { 
          success: true,
          statistics: {
            assignments_made: 5,
            unassigned_shifts: 0,
            conflicts_detected: 0,
            warnings: 0,
          },
          assignments: [],
          conflicts: [],
          warnings: [],
        },
      };
      
      mockScheduleOrchestrationAsync.mockReturnValue(mockResult as any);
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      const scheduleRequest = {
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: 'dept1',
        options: { dry_run: true },
      };

      await act(async () => {
        await result.current.scheduleOrchestration(scheduleRequest);
      });

      expect(mockScheduleOrchestrationAsync).toHaveBeenCalledWith(scheduleRequest);
    });

    it('should handle scheduleOrchestration success', async () => {
      const store = createTestStore();
      const mockPayload = { id: 1, status: 'completed' };
      const mockResult = {
        type: 'orchestrator/scheduleOrchestration/fulfilled',
        payload: mockPayload,
      };
      
      mockedScheduleOrchestrationAsync.mockReturnValue(mockResult as any);
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      let orchestrationResult;
      await act(async () => {
        orchestrationResult = await result.current.scheduleOrchestration({
          start_date: '2024-01-15',
          end_date: '2024-01-21',
        });
      });

      expect(orchestrationResult).toEqual(mockPayload);
    });

    it('should handle scheduleOrchestration error', async () => {
      const store = createTestStore();
      const mockError = 'Orchestration failed';
      const mockResult = {
        type: 'orchestrator/scheduleOrchestration/rejected',
        payload: mockError,
      };
      
      mockedScheduleOrchestrationAsync.mockReturnValue(mockResult as any);
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await expect(
          result.current.scheduleOrchestration({
            start_date: '2024-01-15',
            end_date: '2024-01-21',
          })
        ).rejects.toThrow(mockError);
      });
    });
  });

  describe('Convenience Functions', () => {
    it('should call scheduleCurrentWeek correctly', async () => {
      const store = createTestStore();
      const mockResult = {
        type: 'orchestrator/scheduleOrchestration/fulfilled',
        payload: { id: 1 },
      };
      
      mockedScheduleOrchestrationAsync.mockReturnValue(mockResult as any);
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.scheduleCurrentWeek('dept1', { dry_run: true });
      });

      expect(mockedOrchestratorService.getCurrentWeekRange).toHaveBeenCalled();
      expect(mockedScheduleOrchestrationAsync).toHaveBeenCalledWith({
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: 'dept1',
        options: { dry_run: true },
      });
    });

    it('should call scheduleNextWeek correctly', async () => {
      const store = createTestStore();
      const mockResult = {
        type: 'orchestrator/scheduleOrchestration/fulfilled',
        payload: { id: 1 },
      };
      
      mockedScheduleOrchestrationAsync.mockReturnValue(mockResult as any);
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.scheduleNextWeek('dept2', { force: true });
      });

      expect(mockedOrchestratorService.getNextWeekRange).toHaveBeenCalled();
      expect(mockedScheduleOrchestrationAsync).toHaveBeenCalledWith({
        start_date: '2024-01-22',
        end_date: '2024-01-28',
        department_id: 'dept2',
        options: { force: true },
      });
    });

    it('should call getCoverageForCurrentWeek correctly', async () => {
      const store = createTestStore();
      const mockResult = {
        type: 'orchestrator/getCoverage/fulfilled',
        payload: { coverage: 95 },
      };
      
      mockedGetCoverageAsync.mockReturnValue(mockResult as any);
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.getCoverageForCurrentWeek('dept1');
      });

      expect(mockedOrchestratorService.getCurrentWeekRange).toHaveBeenCalled();
      expect(mockedGetCoverageAsync).toHaveBeenCalledWith({
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        department_id: 'dept1',
      });
    });

    it('should call getAvailabilityForCurrentWeek correctly', async () => {
      const store = createTestStore();
      const mockResult = {
        type: 'orchestrator/getAvailability/fulfilled',
        payload: [{ id: 1, name: 'John Doe' }],
      };
      
      mockedGetAvailabilityAsync.mockReturnValue(mockResult as any);
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.getAvailabilityForCurrentWeek('incidents', 'dept1');
      });

      expect(mockedOrchestratorService.getCurrentWeekRange).toHaveBeenCalled();
      expect(mockedGetAvailabilityAsync).toHaveBeenCalledWith({
        start_date: '2024-01-15',
        end_date: '2024-01-21',
        shift_type: 'incidents',
        department_id: 'dept1',
      });
    });
  });

  describe('System Health and Metrics', () => {
    it('should call refreshSystemHealth correctly', async () => {
      const store = createTestStore();
      const mockResult = {
        type: 'orchestrator/getSystemHealth/fulfilled',
        payload: { status: 'healthy' },
      };
      
      mockedGetSystemHealthAsync.mockReturnValue(mockResult as any);
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.refreshSystemHealth();
      });

      expect(mockedGetSystemHealthAsync).toHaveBeenCalled();
    });

    it('should call refreshMetrics correctly', async () => {
      const store = createTestStore();
      const mockResult = {
        type: 'orchestrator/getSystemMetrics/fulfilled',
        payload: { totalEmployees: 25 },
      };
      
      mockedGetSystemMetricsAsync.mockReturnValue(mockResult as any);
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.refreshMetrics();
      });

      expect(mockedGetSystemMetricsAsync).toHaveBeenCalled();
    });

    it('should correctly identify system health status', () => {
      const healthyStore = createTestStore({
        systemHealth: { status: 'healthy' },
      });
      
      const { result: healthyResult } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(healthyStore),
      });

      expect(healthyResult.current.isSystemHealthy).toBe(true);

      const unhealthyStore = createTestStore({
        systemHealth: { status: 'unhealthy' },
      });
      
      const { result: unhealthyResult } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(unhealthyStore),
      });

      expect(unhealthyResult.current.isSystemHealthy).toBe(false);
    });
  });

  describe('State Management', () => {
    it('should update selectedDateRange correctly', () => {
      const store = createTestStore();
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      const newDateRange = {
        start: new Date('2024-01-15'),
        end: new Date('2024-01-21'),
      };

      act(() => {
        result.current.updateSelectedDateRange(newDateRange);
      });

      expect(result.current.state.selectedDateRange).toEqual(newDateRange);
    });

    it('should update selectedDepartment correctly', () => {
      const store = createTestStore();
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.updateSelectedDepartment('dept1');
      });

      expect(result.current.state.selectedDepartment).toBe('dept1');
    });

    it('should clear error state correctly', () => {
      const store = createTestStore({
        error: 'Some error message',
      });
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.hasError).toBe(true);

      act(() => {
        result.current.clearError();
      });

      expect(result.current.hasError).toBe(false);
    });

    it('should reset state correctly', () => {
      const store = createTestStore({
        lastOrchestration: { id: 1 },
        error: 'Some error',
        selectedDepartment: 'dept1',
      });
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.resetState();
      });

      expect(result.current.state.lastOrchestration).toBeNull();
      expect(result.current.state.error).toBeNull();
      expect(result.current.state.selectedDepartment).toBeNull();
    });
  });

  describe('Status Indicators', () => {
    it('should correctly identify orchestration running status', () => {
      const runningStore = createTestStore({
        orchestrationStatus: 'running',
      });
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(runningStore),
      });

      expect(result.current.isOrchestrationRunning).toBe(true);
    });

    it('should correctly identify if there is last orchestration', () => {
      const withOrchestrationStore = createTestStore({
        lastOrchestration: { id: 1, status: 'completed' },
      });
      
      const { result } = renderHook(() => useOrchestrator(), {
        wrapper: createWrapper(withOrchestrationStore),
      });

      expect(result.current.hasLastOrchestration).toBe(true);
    });
  });
});

describe('useOrchestratorStatus Hook', () => {
  it('should return correct status information', () => {
    const store = createTestStore({
      orchestrationStatus: 'running',
      systemHealth: { status: 'healthy' },
      loading: true,
      error: 'Some error',
    });
    
    const { result } = renderHook(() => useOrchestratorStatus(), {
      wrapper: createWrapper(store),
    });

    expect(result.current.orchestrationStatus).toBe('running');
    expect(result.current.systemHealth).toEqual({ status: 'healthy' });
    expect(result.current.isLoading).toBe(true);
    expect(result.current.hasError).toBe(true);
    expect(result.current.isSystemHealthy).toBe(true);
    expect(result.current.isOrchestrationRunning).toBe(true);
  });
});

describe('useOrchestratorData Hook', () => {
  it('should return correct data information', () => {
    const store = createTestStore({
      lastOrchestration: { id: 1 },
      coverageData: { coverage: 95 },
      availabilityData: [{ id: 1, name: 'John' }],
      systemMetrics: { totalEmployees: 25 },
    });
    
    const { result } = renderHook(() => useOrchestratorData(), {
      wrapper: createWrapper(store),
    });

    expect(result.current.lastOrchestration).toEqual({ id: 1 });
    expect(result.current.coverageData).toEqual({ coverage: 95 });
    expect(result.current.availabilityData).toEqual([{ id: 1, name: 'John' }]);
    expect(result.current.systemMetrics).toEqual({ totalEmployees: 25 });
    expect(result.current.hasData).toBe(true);
  });

  it('should correctly identify when there is no data', () => {
    const store = createTestStore({
      lastOrchestration: null,
      coverageData: null,
      availabilityData: [],
      systemMetrics: null,
    });
    
    const { result } = renderHook(() => useOrchestratorData(), {
      wrapper: createWrapper(store),
    });

    expect(result.current.hasData).toBe(false);
  });
});
