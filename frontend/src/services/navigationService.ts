import { createElement } from 'react';
import {
  Dashboard,
  CalendarMonth,
  Timeline,
  PlayCircle,
  Assessment,
  History,
  People,
  Groups,
  AccountCircle,
  SwapHoriz,
  BeachAccess,
  Settings,
} from '@mui/icons-material';
import { User, userService } from './userService';

export interface NavigationItem {
  text: string;
  iconName: string;
  path: string;
  divider?: boolean;
  permission?: string;
  requiresStaff?: boolean;
  requiresSuperuser?: boolean;
}

const iconMap = {
  Dashboard,
  CalendarMonth,
  Timeline,
  PlayCircle,
  Assessment,
  History,
  People,
  Groups,
  AccountCircle,
  SwapHoriz,
  BeachAccess,
  Settings,
};

const allNavigationItems: NavigationItem[] = [
  { text: 'Dashboard', iconName: 'Dashboard', path: '/dashboard' },
  { text: 'Calendar', iconName: 'CalendarMonth', path: '/calendar' },
  { text: 'Timeline', iconName: 'Timeline', path: '/timeline' },
  { 
    text: 'Orchestrator', 
    iconName: 'PlayCircle', 
    path: '/orchestrator',
    requiresStaff: true 
  },
  { 
    text: 'Fairness Dashboard', 
    iconName: 'Assessment', 
    path: '/fairness',
    requiresStaff: true,
    divider: true
  },
  { 
    text: 'User Management', 
    iconName: 'People', 
    path: '/user-management',
    requiresStaff: true 
  },
  { 
    text: 'Team Management', 
    iconName: 'Groups', 
    path: '/team-management',
    requiresStaff: true 
  },
  { text: 'Profile', iconName: 'AccountCircle', path: '/profile', divider: true },
  { text: 'Shift Swaps', iconName: 'SwapHoriz', path: '/swaps' },
  { text: 'Leave Requests', iconName: 'BeachAccess', path: '/leaves' },
  { text: 'Settings', iconName: 'Settings', path: '/settings' },
];

export const navigationService = {
  getNavigationItems: (user: User | null): NavigationItem[] => {
    if (!user) {
      // Return minimal navigation for unauthenticated users
      return [
        { text: 'Dashboard', iconName: 'Dashboard', path: '/dashboard' },
        { text: 'Profile', iconName: 'AccountCircle', path: '/profile' },
      ];
    }

    return allNavigationItems.filter(item => {
      // Check if item requires staff privileges
      if (item.requiresStaff && !user.is_staff && !user.is_superuser) {
        return false;
      }

      // Check if item requires superuser privileges
      if (item.requiresSuperuser && !user.is_superuser) {
        return false;
      }

      // Check specific permissions
      if (item.permission && !userService.hasPermission(user, item.permission)) {
        return false;
      }

      return true;
    });
  },

  getIcon: (iconName: string) => {
    const IconComponent = iconMap[iconName as keyof typeof iconMap];
    return IconComponent ? createElement(IconComponent) : null;
  },

  canAccessRoute: (user: User | null, path: string): boolean => {
    if (!user) return false;

    const item = allNavigationItems.find(item => item.path === path);
    if (!item) return true; // Allow access to unknown routes

    if (item.requiresStaff && !user.is_staff && !user.is_superuser) {
      return false;
    }

    if (item.requiresSuperuser && !user.is_superuser) {
      return false;
    }

    if (item.permission && !userService.hasPermission(user, item.permission)) {
      return false;
    }

    return true;
  },
};
