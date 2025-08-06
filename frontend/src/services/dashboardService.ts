import { apiClient } from './apiClient';
import { UserDashboardData } from './userService';

export interface DashboardData {
  incident_engineer: Engineer | null;
  incident_standby_engineer: Engineer | null;
  waakdienst_engineer: Engineer | null;
  engineers_working: Engineer[];
  engineers_working_count: number;
  total_engineers: number;
  available_engineers: number;
  engineers_on_leave: number;
}

export interface Engineer {
  id: number;
  name: string;
  username: string;
}

export const dashboardService = {
  getDashboardData: async (): Promise<DashboardData> => {
    return apiClient.get('/shifts/api/dashboard/');
  },

  getUserDashboardData: async (): Promise<UserDashboardData> => {
    return apiClient.get('/api/users/me/dashboard/');
  },
};
