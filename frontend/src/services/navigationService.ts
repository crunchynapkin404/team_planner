import { createElement } from 'react';
import {
  Dashboard,
  CalendarMonth,
  Timeline,
  PlayCircle,
  Assessment,
  BarChart,
  History,
  People,
  Groups,
  AccountCircle,
  SwapHoriz,
  BeachAccess,
  Settings,
  Security,
  Repeat,
  Warning,
  CheckCircle,
} from '@mui/icons-material';
import { User, userService } from './userService';

export interface NavigationItem {
  text: string;
  iconName: string;
  path: string;
  divider?: boolean;
  permission?: string | string[]; // Single or multiple permissions
  role?: string | string[]; // Single or multiple roles
  requiresAny?: boolean; // If true, requires any permission/role, otherwise requires all
  requiresStaff?: boolean;
  requiresSuperuser?: boolean;
}

const iconMap = {
  Dashboard,
  CalendarMonth,
  Timeline,
  PlayCircle,
  Assessment,
  BarChart,
  History,
  People,
  Groups,
  AccountCircle,
  SwapHoriz,
  BeachAccess,
  Settings,
  Repeat,
  Security,
  Warning,
  CheckCircle,
};

const allNavigationItems: NavigationItem[] = [
  { 
    text: 'Dashboard', 
    iconName: 'Dashboard', 
    path: '/dashboard' 
  },
  { 
    text: 'Calendar', 
    iconName: 'CalendarMonth', 
    path: '/calendar',
    permission: 'can_view_schedule'
  },
  { 
    text: 'Timeline', 
    iconName: 'Timeline', 
    path: '/timeline',
    permission: 'can_view_schedule'
  },
  { 
    text: 'Orchestrator', 
    iconName: 'PlayCircle', 
    path: '/orchestrator',
    permission: 'can_run_orchestrator'
  },
  { 
    text: 'Fairness Dashboard', 
    iconName: 'Assessment', 
    path: '/fairness',
    permission: ['can_view_analytics', 'can_view_schedule'],
    requiresAny: false, // Requires both permissions
  },
  { 
    text: 'Reports', 
    iconName: 'BarChart', 
    path: '/reports',
    permission: ['can_run_orchestrator', 'can_manage_team'],
    requiresAny: true, // User needs at least one of these permissions
  },
  { 
    text: 'Recurring Patterns', 
    iconName: 'Repeat', 
    path: '/patterns',
    permission: ['can_run_orchestrator', 'can_manage_team'],
    requiresAny: true, // User needs at least one of these permissions
  },
  { 
    text: 'Template Library', 
    iconName: 'History', 
    path: '/templates',
    permission: ['can_run_orchestrator', 'can_manage_team'],
    requiresAny: true, // User needs at least one of these permissions
  },
  { 
    text: 'Bulk Operations', 
    iconName: 'DynamicFeed', 
    path: '/bulk-operations',
    permission: ['can_run_orchestrator', 'can_manage_team'],
    requiresAny: true, // User needs at least one of these permissions
  },
  { 
    text: 'Management', 
    iconName: 'Security', 
    path: '/management',
    permission: ['can_manage_users', 'can_manage_team', 'can_assign_roles'],
    requiresAny: true, // User needs at least one of these permissions
    divider: true
  },
  { 
    text: 'Profile', 
    iconName: 'AccountCircle', 
    path: '/profile' 
  },
  { 
    text: 'Shift Swaps', 
    iconName: 'SwapHoriz', 
    path: '/swaps',
    permission: 'can_request_shift_swap'
  },
  { 
    text: 'Leave Requests', 
    iconName: 'BeachAccess', 
    path: '/leaves',
    permission: 'can_request_leave'
  },
  { 
    text: 'Leave Conflicts', 
    iconName: 'Warning', 
    path: '/leave-conflicts',
    permission: 'can_approve_leave'
  },
  { 
    text: 'Approval Rules', 
    iconName: 'Security', 
    path: '/approval-rules',
    permission: ['can_manage_users', 'can_manage_team'],
    requiresAny: true,
  },
  { 
    text: 'Pending Approvals', 
    iconName: 'CheckCircle', 
    path: '/pending-approvals',
    permission: 'can_approve_shift_swap'
  },
  { 
    text: 'Settings', 
    iconName: 'Settings', 
    path: '/settings' 
  },
];

// Helper function to check if user has required permissions
const hasRequiredPermissions = (
  user: User,
  permission?: string | string[],
  requiresAny?: boolean
): boolean => {
  if (!permission) return true;

  const permissions = Array.isArray(permission) ? permission : [permission];
  
  if (requiresAny) {
    // User needs at least one of the permissions
    return permissions.some(perm => userService.hasPermission(user, perm));
  } else {
    // User needs all of the permissions
    return permissions.every(perm => userService.hasPermission(user, perm));
  }
};

// Helper function to check if user can access an item
const canAccessItem = (user: User | null, item: NavigationItem): boolean => {
  if (!user) return false;

  // Check if item requires staff privileges
  if (item.requiresStaff && !user.is_staff && !user.is_superuser) {
    return false;
  }

  // Check if item requires superuser privileges
  if (item.requiresSuperuser && !user.is_superuser) {
    return false;
  }

  // Check specific permissions
  if (item.permission && !hasRequiredPermissions(user, item.permission, item.requiresAny)) {
    return false;
  }

  return true;
};

export const navigationService = {
  getNavigationItems: (user: User | null): NavigationItem[] => {
    if (!user) {
      // Return minimal navigation for unauthenticated users
      return [
        { text: 'Dashboard', iconName: 'Dashboard', path: '/dashboard' },
        { text: 'Profile', iconName: 'AccountCircle', path: '/profile' },
      ];
    }

    return allNavigationItems.filter(item => canAccessItem(user, item));
  },

  getIcon: (iconName: string) => {
    const IconComponent = iconMap[iconName as keyof typeof iconMap];
    return IconComponent ? createElement(IconComponent) : null;
  },

  canAccessRoute: (user: User | null, path: string): boolean => {
    if (!user) return false;

    const item = allNavigationItems.find(item => item.path === path);
    if (!item) return true; // Allow access to unknown routes

    return canAccessItem(user, item);
  },
};
