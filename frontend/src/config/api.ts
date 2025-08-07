// API Configuration for different environments
export const API_CONFIG = {
  // Base API URL - using empty string to rely on proxy configuration
  BASE_URL: '',
  
  // Base API URLs that work with proxy configuration
  BASE_URLS: {
    MAIN_API: '/api',                    // User, leaves, etc. -> proxy to http://localhost:8000/api
    SHIFTS_API: '/shifts/api',           // Shifts endpoints -> proxy to http://localhost:8000/shifts/api
    LEAVES_API: '/api/leaves',           // Leaves endpoints -> proxy to http://localhost:8000/api/leaves
    ORCHESTRATORS_API: '/orchestrators/api', // Orchestrator endpoints -> proxy to http://localhost:8000/orchestrators/api
  },

  // Specific endpoints
  ENDPOINTS: {
    // Authentication
    AUTH_TOKEN: '/api/auth-token/',
    AUTH_LOGOUT: '/api/auth/logout/',
    
    // User management
    USERS_ME: '/api/users/me/',
    USERS_LIST: '/api/users/',
    USER_DETAIL: '/api/users/{id}/',
    
    // Dashboard
    SHIFTS_DASHBOARD: '/shifts/api/dashboard/',
    USERS_DASHBOARD: '/api/users/me/dashboard/',
    
    // Teams
    TEAMS_LIST: '/api/teams/',
    TEAM_DETAIL: '/api/teams/{id}/',
    TEAM_MEMBERS: '/api/teams/{teamId}/members/',
    TEAM_MEMBER: '/api/teams/{teamId}/members/{memberId}/',
    
    // Departments
    DEPARTMENTS_LIST: '/api/departments/',
    
    // Shifts
    SHIFTS_LIST: '/shifts/api/shifts/',
    SHIFTS_USER_UPCOMING: '/shifts/api/user/upcoming-shifts/',
    SHIFTS_USER_INCOMING_SWAPS: '/shifts/api/user/incoming-swap-requests/',
    SHIFTS_USER_OUTGOING_SWAPS: '/shifts/api/user/outgoing-swap-requests/',
    SHIFTS_SWAP_REQUESTS_RESPOND: '/shifts/api/swap-requests/{id}/respond/',
    SHIFTS_SWAP_REQUESTS_CREATE: '/shifts/api/swap-requests/create/',
    SHIFTS_SWAP_REQUESTS_BULK_CREATE: '/shifts/api/swap-requests/bulk-create/',
    SHIFTS_USER_SHIFTS: '/shifts/api/user/shifts/',
    SHIFTS_TEAM_MEMBERS: '/shifts/api/team-members/',
    SHIFTS_EMPLOYEE: '/shifts/api/employee-shifts/',
    
    // Leaves  
    LEAVES_REQUESTS: '/api/leaves/requests/',
    LEAVES_REQUEST_DETAIL: '/api/leaves/requests/{id}/',
    LEAVES_REQUEST_CREATE: '/api/leaves/requests/create/',
    LEAVES_REQUEST_APPROVE: '/api/leaves/requests/{id}/approve/',
    LEAVES_REQUEST_REJECT: '/api/leaves/requests/{id}/reject/',
    LEAVES_REQUEST_CANCEL: '/api/leaves/requests/{id}/cancel/',
    LEAVES_TYPES: '/api/leaves/leave-types/',
    LEAVES_CONFLICTING_SHIFTS: '/api/leaves/requests/{id}/conflicting-shifts/',
    LEAVES_CHECK_CONFLICTS: '/api/leaves/requests/check_conflicts/',
    LEAVES_USER_STATS: '/api/leaves/requests/user_stats/',
    
    // Orchestrators
    ORCHESTRATOR_CREATE: '/orchestrators/api/create/',
    ORCHESTRATOR_APPLY_PREVIEW: '/orchestrators/api/apply-preview/',
    ORCHESTRATOR_STATUS: '/orchestrators/api/status/',
    ORCHESTRATOR_FAIRNESS: '/orchestrators/api/fairness/',
  }
};

// Helper function to replace placeholders in endpoint URLs
export const buildEndpointUrl = (endpoint: string, params: Record<string, string | number> = {}): string => {
  let url = endpoint;
  Object.entries(params).forEach(([key, value]) => {
    url = url.replace(`{${key}}`, String(value));
  });
  return url;
};
