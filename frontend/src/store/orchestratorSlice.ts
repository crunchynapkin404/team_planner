/**
 * Orchestrator Redux Slice - State Management for Clean Architecture API
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { OrchestratorService } from '../services/orchestratorService';
import type {
  OrchestratorState,
  ScheduleRequest,
  OrchestrationResult,
  CoverageAnalysis,
  AvailabilityParams,
  AvailabilityResponse,
  SystemHealth,
  SystemMetrics,
} from '../types/orchestrator';

// Initial state
const initialState: OrchestratorState = {
  // Orchestration state
  orchestrationStatus: 'idle',
  lastOrchestration: null,
  orchestrationHistory: [],
  
  // Coverage state
  coverageData: null,
  coverageLoading: false,
  
  // Availability state
  availabilityData: [],
  availabilityLoading: false,
  
  // System monitoring
  systemHealth: null,
  systemMetrics: null,
  
  // UI state
  loading: false,
  error: null,
  selectedDateRange: { start: null, end: null },
  selectedDepartment: null,
};

// Async thunks for API calls
export const scheduleOrchestrationAsync = createAsyncThunk(
  'orchestrator/scheduleOrchestration',
  async (request: ScheduleRequest, { rejectWithValue }) => {
    try {
      const validationErrors = OrchestratorService.validateScheduleRequest(request);
      if (validationErrors.length > 0) {
        throw new Error(validationErrors.join(', '));
      }
      
      const result = await OrchestratorService.scheduleOrchestration(request);
      return result;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to schedule orchestration');
    }
  }
);

export const getCoverageAsync = createAsyncThunk(
  'orchestrator/getCoverage',
  async (params: { start_date: string; end_date: string; department_id?: string }, { rejectWithValue }) => {
    try {
      const result = await OrchestratorService.getCoverage(params);
      return result;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to get coverage data');
    }
  }
);

export const getAvailabilityAsync = createAsyncThunk(
  'orchestrator/getAvailability',
  async (params: AvailabilityParams, { rejectWithValue }) => {
    try {
      const result = await OrchestratorService.getAvailability(params);
      return result;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to get availability data');
    }
  }
);

export const getSystemHealthAsync = createAsyncThunk(
  'orchestrator/getSystemHealth',
  async (_, { rejectWithValue }) => {
    try {
      const result = await OrchestratorService.getSystemHealth();
      return result;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to get system health');
    }
  }
);

export const getSystemMetricsAsync = createAsyncThunk(
  'orchestrator/getSystemMetrics',
  async (_, { rejectWithValue }) => {
    try {
      const result = await OrchestratorService.getSystemMetrics();
      return result;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to get system metrics');
    }
  }
);

// Redux slice
const orchestratorSlice = createSlice({
  name: 'orchestrator',
  initialState,
  reducers: {
    // UI actions
    clearError: (state) => {
      state.error = null;
    },
    
    setSelectedDateRange: (state, action: PayloadAction<{ start: Date | null; end: Date | null }>) => {
      state.selectedDateRange = action.payload;
    },
    
    setSelectedDepartment: (state, action: PayloadAction<string | null>) => {
      state.selectedDepartment = action.payload;
    },
    
    clearOrchestrationHistory: (state) => {
      state.orchestrationHistory = [];
    },
    
    clearCoverageData: (state) => {
      state.coverageData = null;
    },
    
    clearAvailabilityData: (state) => {
      state.availabilityData = [];
    },
    
    // Reset all state
    resetOrchestratorState: () => initialState,
  },
  extraReducers: (builder) => {
    // Schedule Orchestration
    builder
      .addCase(scheduleOrchestrationAsync.pending, (state) => {
        state.orchestrationStatus = 'running';
        state.loading = true;
        state.error = null;
      })
      .addCase(scheduleOrchestrationAsync.fulfilled, (state, action: PayloadAction<OrchestrationResult>) => {
        state.orchestrationStatus = 'success';
        state.loading = false;
        state.lastOrchestration = action.payload;
        state.orchestrationHistory.unshift(action.payload);
        
        // Keep only last 10 orchestration results
        if (state.orchestrationHistory.length > 10) {
          state.orchestrationHistory = state.orchestrationHistory.slice(0, 10);
        }
      })
      .addCase(scheduleOrchestrationAsync.rejected, (state, action) => {
        state.orchestrationStatus = 'error';
        state.loading = false;
        state.error = action.payload as string;
      });

    // Get Coverage
    builder
      .addCase(getCoverageAsync.pending, (state) => {
        state.coverageLoading = true;
        state.error = null;
      })
      .addCase(getCoverageAsync.fulfilled, (state, action: PayloadAction<CoverageAnalysis>) => {
        state.coverageLoading = false;
        state.coverageData = action.payload;
      })
      .addCase(getCoverageAsync.rejected, (state, action) => {
        state.coverageLoading = false;
        state.error = action.payload as string;
      });

    // Get Availability
    builder
      .addCase(getAvailabilityAsync.pending, (state) => {
        state.availabilityLoading = true;
        state.error = null;
      })
      .addCase(getAvailabilityAsync.fulfilled, (state, action: PayloadAction<AvailabilityResponse>) => {
        state.availabilityLoading = false;
        state.availabilityData = action.payload.available_employees;
      })
      .addCase(getAvailabilityAsync.rejected, (state, action) => {
        state.availabilityLoading = false;
        state.error = action.payload as string;
      });

    // Get System Health
    builder
      .addCase(getSystemHealthAsync.fulfilled, (state, action: PayloadAction<SystemHealth>) => {
        state.systemHealth = action.payload;
      })
      .addCase(getSystemHealthAsync.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Get System Metrics
    builder
      .addCase(getSystemMetricsAsync.fulfilled, (state, action: PayloadAction<SystemMetrics>) => {
        state.systemMetrics = action.payload;
      })
      .addCase(getSystemMetricsAsync.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

// Export actions
export const {
  clearError,
  setSelectedDateRange,
  setSelectedDepartment,
  clearOrchestrationHistory,
  clearCoverageData,
  clearAvailabilityData,
  resetOrchestratorState,
} = orchestratorSlice.actions;

// Export selectors
export const selectOrchestratorState = (state: { orchestrator: OrchestratorState }) => state.orchestrator;
export const selectOrchestrationStatus = (state: { orchestrator: OrchestratorState }) => state.orchestrator.orchestrationStatus;
export const selectLastOrchestration = (state: { orchestrator: OrchestratorState }) => state.orchestrator.lastOrchestration;
export const selectOrchestrationHistory = (state: { orchestrator: OrchestratorState }) => state.orchestrator.orchestrationHistory;
export const selectCoverageData = (state: { orchestrator: OrchestratorState }) => state.orchestrator.coverageData;
export const selectAvailabilityData = (state: { orchestrator: OrchestratorState }) => state.orchestrator.availabilityData;
export const selectSystemHealth = (state: { orchestrator: OrchestratorState }) => state.orchestrator.systemHealth;
export const selectSystemMetrics = (state: { orchestrator: OrchestratorState }) => state.orchestrator.systemMetrics;
export const selectIsLoading = (state: { orchestrator: OrchestratorState }) => 
  state.orchestrator.loading || state.orchestrator.coverageLoading || state.orchestrator.availabilityLoading;
export const selectError = (state: { orchestrator: OrchestratorState }) => state.orchestrator.error;
export const selectSelectedDateRange = (state: { orchestrator: OrchestratorState }) => state.orchestrator.selectedDateRange;
export const selectSelectedDepartment = (state: { orchestrator: OrchestratorState }) => state.orchestrator.selectedDepartment;

// Export reducer
export default orchestratorSlice.reducer;
