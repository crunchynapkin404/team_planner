/**
 * Custom Hook for Orchestrator Operations
 * Provides a clean interface for components to interact with orchestrator functionality
 */

import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch } from '../store';
import {
  scheduleOrchestrationAsync,
  getCoverageAsync,
  getAvailabilityAsync,
  getSystemHealthAsync,
  getSystemMetricsAsync,
  clearError,
  setSelectedDateRange,
  setSelectedDepartment,
  clearOrchestrationHistory,
  clearCoverageData,
  clearAvailabilityData,
  resetOrchestratorState,
  selectOrchestratorState,
  selectOrchestrationStatus,
  selectLastOrchestration,
  selectOrchestrationHistory,
  selectCoverageData,
  selectAvailabilityData,
  selectSystemHealth,
  selectSystemMetrics,
  selectIsLoading,
  selectError,
  selectSelectedDateRange,
  selectSelectedDepartment,
} from '../store/orchestratorSlice';
import { OrchestratorService } from '../services/orchestratorService';
import type {
  ScheduleRequest,
  AvailabilityParams,
  UseOrchestratorReturn,
} from '../types/orchestrator';

export const useOrchestrator = (): UseOrchestratorReturn => {
  const dispatch = useDispatch<AppDispatch>();
  
  // Selectors
  const state = useSelector(selectOrchestratorState);
  const orchestrationStatus = useSelector(selectOrchestrationStatus);
  const lastOrchestration = useSelector(selectLastOrchestration);
  const orchestrationHistory = useSelector(selectOrchestrationHistory);
  const coverageData = useSelector(selectCoverageData);
  const availabilityData = useSelector(selectAvailabilityData);
  const systemHealth = useSelector(selectSystemHealth);
  const systemMetrics = useSelector(selectSystemMetrics);
  const isLoading = useSelector(selectIsLoading);
  const error = useSelector(selectError);
  const selectedDateRange = useSelector(selectSelectedDateRange);
  const selectedDepartment = useSelector(selectSelectedDepartment);

  // Actions
  const scheduleOrchestration = useCallback(async (request: ScheduleRequest) => {
    const result = await dispatch(scheduleOrchestrationAsync(request));
    if (scheduleOrchestrationAsync.fulfilled.match(result)) {
      return result.payload;
    } else {
      throw new Error(result.payload as string);
    }
  }, [dispatch]);

  const getCoverage = useCallback(async (params: { start_date: string; end_date: string; department_id?: string }) => {
    const result = await dispatch(getCoverageAsync(params));
    if (getCoverageAsync.fulfilled.match(result)) {
      return result.payload;
    } else {
      throw new Error(result.payload as string);
    }
  }, [dispatch]);

  const getAvailability = useCallback(async (params: AvailabilityParams) => {
    const result = await dispatch(getAvailabilityAsync(params));
    if (getAvailabilityAsync.fulfilled.match(result)) {
      return result.payload;
    } else {
      throw new Error(result.payload as string);
    }
  }, [dispatch]);

  const refreshSystemHealth = useCallback(async () => {
    const result = await dispatch(getSystemHealthAsync());
    if (getSystemHealthAsync.fulfilled.match(result)) {
      return result.payload;
    } else {
      throw new Error(result.payload as string);
    }
  }, [dispatch]);

  const refreshMetrics = useCallback(async () => {
    const result = await dispatch(getSystemMetricsAsync());
    if (getSystemMetricsAsync.fulfilled.match(result)) {
      return result.payload;
    } else {
      throw new Error(result.payload as string);
    }
  }, [dispatch]);

  // UI Actions
  const clearErrorState = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  const updateSelectedDateRange = useCallback((dateRange: { start: Date | null; end: Date | null }) => {
    dispatch(setSelectedDateRange(dateRange));
  }, [dispatch]);

  const updateSelectedDepartment = useCallback((departmentId: string | null) => {
    dispatch(setSelectedDepartment(departmentId));
  }, [dispatch]);

  const clearHistory = useCallback(() => {
    dispatch(clearOrchestrationHistory());
  }, [dispatch]);

  const clearCoverage = useCallback(() => {
    dispatch(clearCoverageData());
  }, [dispatch]);

  const clearAvailability = useCallback(() => {
    dispatch(clearAvailabilityData());
  }, [dispatch]);

  const resetState = useCallback(() => {
    dispatch(resetOrchestratorState());
  }, [dispatch]);

  // Convenience functions
  const scheduleCurrentWeek = useCallback(async (departmentId?: string, options?: { dry_run?: boolean; force?: boolean }) => {
    const dateRange = OrchestratorService.getCurrentWeekRange();
    const request: ScheduleRequest = {
      ...dateRange,
      department_id: departmentId,
      options,
    };
    return scheduleOrchestration(request);
  }, [scheduleOrchestration]);

  const scheduleNextWeek = useCallback(async (departmentId?: string, options?: { dry_run?: boolean; force?: boolean }) => {
    const dateRange = OrchestratorService.getNextWeekRange();
    const request: ScheduleRequest = {
      ...dateRange,
      department_id: departmentId,
      options,
    };
    return scheduleOrchestration(request);
  }, [scheduleOrchestration]);

  const scheduleCustomDateRange = useCallback(async (
    startDate: Date,
    endDate: Date,
    departmentId?: string,
    options?: { dry_run?: boolean; force?: boolean }
  ) => {
    const dateRange = OrchestratorService.getCustomDateRange(startDate, endDate);
    const request: ScheduleRequest = {
      ...dateRange,
      department_id: departmentId,
      options,
    };
    return scheduleOrchestration(request);
  }, [scheduleOrchestration]);

  const getCoverageForCurrentWeek = useCallback(async (departmentId?: string) => {
    const dateRange = OrchestratorService.getCurrentWeekRange();
    return getCoverage({ ...dateRange, department_id: departmentId });
  }, [getCoverage]);

  const getCoverageForNextWeek = useCallback(async (departmentId?: string) => {
    const dateRange = OrchestratorService.getNextWeekRange();
    return getCoverage({ ...dateRange, department_id: departmentId });
  }, [getCoverage]);

  const getCoverageForCustomRange = useCallback(async (startDate: Date, endDate: Date, departmentId?: string) => {
    const dateRange = OrchestratorService.getCustomDateRange(startDate, endDate);
    return getCoverage({ ...dateRange, department_id: departmentId });
  }, [getCoverage]);

  const getAvailabilityForCurrentWeek = useCallback(async (shiftType?: string, departmentId?: string) => {
    const dateRange = OrchestratorService.getCurrentWeekRange();
    const params: AvailabilityParams = {
      ...dateRange,
      shift_type: shiftType as any,
      department_id: departmentId,
    };
    return getAvailability(params);
  }, [getAvailability]);

  // Status checks
  const isOrchestrationRunning = orchestrationStatus === 'running';
  const hasError = !!error;
  const hasLastOrchestration = !!lastOrchestration;
  const isSystemHealthy = systemHealth?.status === 'healthy';

  // Summary functions
  const getOrchestrationSummary = useCallback(() => {
    if (!lastOrchestration) return null;
    return OrchestratorService.getOrchestrationSummary(lastOrchestration);
  }, [lastOrchestration]);

  const getCoverageSummary = useCallback(() => {
    if (!coverageData) return null;
    return OrchestratorService.getCoverageSummary(coverageData);
  }, [coverageData]);

  return {
    // State
    state: {
      orchestrationStatus,
      lastOrchestration,
      orchestrationHistory,
      coverageData,
      coverageLoading: state.coverageLoading,
      availabilityData,
      availabilityLoading: state.availabilityLoading,
      systemHealth,
      systemMetrics,
      loading: state.loading,
      error,
      selectedDateRange,
      selectedDepartment,
    },
    
    // Core Actions
    scheduleOrchestration,
    getCoverage,
    getAvailability,
    refreshSystemHealth,
    refreshMetrics,
    
    // UI Actions
    clearError: clearErrorState,
    updateSelectedDateRange,
    updateSelectedDepartment,
    clearHistory,
    clearCoverage,
    clearAvailability,
    resetState,
    
    // Convenience Actions
    scheduleCurrentWeek,
    scheduleNextWeek,
    scheduleCustomDateRange,
    getCoverageForCurrentWeek,
    getCoverageForNextWeek,
    getCoverageForCustomRange,
    getAvailabilityForCurrentWeek,
    
    // Status Checks
    isLoading,
    hasError,
    isOrchestrationRunning,
    hasLastOrchestration,
    isSystemHealthy,
    
    // Summary Functions
    getOrchestrationSummary,
    getCoverageSummary,
  };
};

// Additional utility hooks
export const useOrchestratorStatus = () => {
  const orchestrationStatus = useSelector(selectOrchestrationStatus);
  const systemHealth = useSelector(selectSystemHealth);
  const isLoading = useSelector(selectIsLoading);
  const error = useSelector(selectError);
  
  return {
    orchestrationStatus,
    systemHealth,
    isLoading,
    hasError: !!error,
    isSystemHealthy: systemHealth?.status === 'healthy',
    isOrchestrationRunning: orchestrationStatus === 'running',
  };
};

export const useOrchestratorData = () => {
  const lastOrchestration = useSelector(selectLastOrchestration);
  const coverageData = useSelector(selectCoverageData);
  const availabilityData = useSelector(selectAvailabilityData);
  const systemMetrics = useSelector(selectSystemMetrics);
  
  return {
    lastOrchestration,
    coverageData,
    availabilityData,
    systemMetrics,
    hasData: !!(lastOrchestration || coverageData || availabilityData?.length),
  };
};
