import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { configureStore } from '@reduxjs/toolkit';
import CssBaseline from '@mui/material/CssBaseline';

import theme from '../theme';
import orchestratorReducer from '../store/orchestratorSlice';
import authReducer from '../store/slices/authSlice';

// Create a test store
export function createTestStore(preloadedState?: any) {
  return configureStore({
    reducer: {
      auth: authReducer,
      orchestrator: orchestratorReducer,
    } as any,
    preloadedState,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
      }),
  });
}

// Test wrapper with all providers
interface TestProvidersProps {
  children: React.ReactNode;
  initialState?: any;
}

export function TestProviders({ children, initialState }: TestProvidersProps) {
  const store = createTestStore(initialState);

  return (
    <Provider store={store}>
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </BrowserRouter>
    </Provider>
  );
}

// Custom render function with providers
export function renderWithProviders(
  ui: React.ReactElement,
  options?: {
    initialState?: any;
    renderOptions?: Omit<RenderOptions, 'wrapper'>;
  }
) {
  const { initialState, renderOptions } = options || {};

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <TestProviders initialState={initialState}>{children}</TestProviders>;
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}

// Mock user for auth state
export const mockUser = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  name: 'Test User',
  is_staff: true,
  is_superuser: false,
  is_active: true,
};

// Mock orchestrator state
export const mockOrchestratorState = {
  orchestrationStatus: 'idle' as const,
  lastOrchestration: null,
  orchestrationHistory: [],
  coverageData: [],
  coverageLoading: false,
  availabilityData: [],
  availabilityLoading: false,
  systemHealth: {
    status: 'healthy' as const,
    timestamp: '2023-12-01T10:00:00Z',
    version: '1.0.0',
    components: {
      database: 'healthy' as const,
      orchestrator: 'healthy' as const,
      cache: 'healthy' as const,
    },
  },
  systemMetrics: {
    total_active_employees: 25,
    total_shifts_last_30_days: 120,
    assigned_shifts_last_30_days: 115,
    assignment_rate_percentage: 95.8,
    unassigned_shifts_last_30_days: 5,
    average_orchestration_time_seconds: 2.3,
    timestamp: '2023-12-01T10:00:00Z',
  },
  loading: false,
  error: null,
  selectedDateRange: { start: null, end: null },
  selectedDepartment: null,
};

// Export everything
export * from '@testing-library/react';
export { renderWithProviders as render };
