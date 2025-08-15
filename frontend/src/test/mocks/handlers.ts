// MSW Handlers for API Integration Testing
import { http, HttpResponse } from 'msw';
import { API_CONFIG } from '../../config/api';

// Mock data for testing
const mockScheduleResult = {
  id: 'schedule-123',
  status: 'completed',
  result: {
    assignments: [
      {
        id: 1,
        user: { id: 1, name: 'John Doe' },
        shift: { id: 1, name: 'Morning Shift', start_time: '09:00', end_time: '17:00' },
        date: '2024-01-15',
        created_at: '2024-01-15T10:00:00Z'
      }
    ],
    statistics: {
      total_shifts: 10,
      assigned_shifts: 8,
      coverage_percentage: 80
    }
  },
  created_at: '2024-01-15T10:00:00Z'
};

const mockCoverageData = {
  coverage_stats: {
    total_shifts: 50,
    covered_shifts: 42,
    uncovered_shifts: 8,
    coverage_percentage: 84.0
  },
  daily_coverage: [
    { date: '2024-01-15', total_shifts: 5, covered_shifts: 4, coverage_percentage: 80.0 },
    { date: '2024-01-16', total_shifts: 6, covered_shifts: 6, coverage_percentage: 100.0 }
  ],
  shift_coverage: [
    { shift_id: 1, shift_name: 'Morning Shift', covered: true, assigned_user: 'John Doe' },
    { shift_id: 2, shift_name: 'Evening Shift', covered: false, assigned_user: null }
  ]
};

const mockAvailabilityData = {
  available_users: [
    { id: 1, name: 'John Doe', available_hours: 40, conflicts: [] },
    { id: 2, name: 'Jane Smith', available_hours: 35, conflicts: ['leave-request-1'] }
  ],
  availability_stats: {
    total_users: 10,
    available_users: 8,
    unavailable_users: 2,
    average_availability_hours: 37.5
  },
  constraints: {
    leave_requests: 2,
    partial_availability: 1,
    skill_mismatches: 0
  }
};

const mockHealthData = {
  status: 'healthy',
  version: '2.0.0',
  database_status: 'connected',
  redis_status: 'connected',
  last_health_check: '2024-01-15T10:00:00Z',
  uptime_seconds: 86400
};

const mockMetricsData = {
  orchestrator_runs: {
    total: 150,
    successful: 142,
    failed: 8,
    success_rate: 94.67
  },
  performance: {
    average_execution_time: 12.5,
    last_execution_time: 15.2,
    fastest_execution: 8.1,
    slowest_execution: 25.3
  },
  coverage: {
    average_coverage: 87.2,
    best_coverage: 95.8,
    worst_coverage: 72.4
  },
  timestamp: '2024-01-15T10:00:00Z'
};

export const handlers = [
  // V2 Orchestrator API endpoints
  http.post(API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_SCHEDULE, async ({ request }) => {
    const body = await request.json();
    
    // Simulate different responses based on request data
    if (body && typeof body === 'object' && 'department_id' in body && body.department_id === '999') {
      return HttpResponse.json(
        { detail: 'Team not found' },
        { status: 404 }
      );
    }
    
    if (body && typeof body === 'object' && 'start_date' in body && body.start_date === 'invalid-date') {
      return HttpResponse.json(
        { detail: 'Invalid date format' },
        { status: 400 }
      );
    }
    
    return HttpResponse.json(mockScheduleResult);
  }),

  http.get(API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_COVERAGE, ({ request }) => {
    const url = new URL(request.url);
    const departmentId = url.searchParams.get('department_id');
    
    if (departmentId === '999') {
      return HttpResponse.json(
        { detail: 'Team not found' },
        { status: 404 }
      );
    }
    
    return HttpResponse.json(mockCoverageData);
  }),

  http.get(API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_AVAILABILITY, ({ request }) => {
    const url = new URL(request.url);
    const departmentId = url.searchParams.get('department_id');
    
    if (departmentId === '999') {
      return HttpResponse.json(
        { detail: 'Team not found' },
        { status: 404 }
      );
    }
    
    return HttpResponse.json(mockAvailabilityData);
  }),

  http.get(API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_HEALTH, () => {
    return HttpResponse.json(mockHealthData);
  }),

  http.get(API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_METRICS, () => {
    return HttpResponse.json(mockMetricsData);
  }),

  // Error simulation handlers
  http.post('/api/orchestrator/schedule/error-500', () => {
    return HttpResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }),

  http.get('/api/orchestrator/coverage/network-error', () => {
    return HttpResponse.error();
  }),

  // Authentication endpoints
  http.post(API_CONFIG.ENDPOINTS.AUTH_TOKEN, async ({ request }) => {
    const body = await request.json();
    
    if (body && typeof body === 'object' && 'username' in body && body.username === 'testuser') {
      return HttpResponse.json({
        token: 'test-token-12345',
        user: { id: 1, username: 'testuser', email: 'test@example.com' }
      });
    }
    
    return HttpResponse.json(
      { detail: 'Invalid credentials' },
      { status: 401 }
    );
  }),
];

// Handlers for error scenarios
export const errorHandlers = [
  http.post(API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_SCHEDULE, () => {
    return HttpResponse.json(
      { detail: 'Service temporarily unavailable' },
      { status: 503 }
    );
  }),
  
  http.get(API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_COVERAGE, () => {
    return HttpResponse.error();
  }),
  
  http.get(API_CONFIG.ENDPOINTS.ORCHESTRATOR_V2_AVAILABILITY, () => {
    return HttpResponse.json(
      { detail: 'Database connection timeout' },
      { status: 500 }
    );
  }),
];
