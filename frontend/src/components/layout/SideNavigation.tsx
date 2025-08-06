import React from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Box,
} from '@mui/material';
import {
  Dashboard,
  People,
  CalendarMonth,
  Timeline,
  SwapHoriz,
  BeachAccess,
  Settings,
  PlayCircle,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

const drawerWidth = 240;

interface NavigationItem {
  text: string;
  icon: React.ReactElement;
  path: string;
  divider?: boolean;
}

const navigationItems: NavigationItem[] = [
  { text: 'Dashboard', icon: <Dashboard />, path: '/dashboard' },
  { text: 'Calendar', icon: <CalendarMonth />, path: '/calendar' },
  { text: 'Timeline', icon: <Timeline />, path: '/timeline' },
  { text: 'Orchestrator', icon: <PlayCircle />, path: '/orchestrator' },
  { text: 'Employees', icon: <People />, path: '/employees' },
  { text: 'Shift Swaps', icon: <SwapHoriz />, path: '/swaps' },
  { text: 'Leave Requests', icon: <BeachAccess />, path: '/leaves' },
  { text: 'Settings', icon: <Settings />, path: '/settings', divider: true },
];

const SideNavigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          top: '64px', // Height of AppBar
        },
      }}
    >
      <Box sx={{ p: 2 }}>
        <Typography variant="h6" color="text.secondary">
          Navigation
        </Typography>
      </Box>
      <Divider />
      <List>
        {navigationItems.map((item) => (
          <React.Fragment key={item.text}>
            {item.divider && <Divider sx={{ my: 1 }} />}
            <ListItem disablePadding>
              <ListItemButton
                selected={location.pathname === item.path}
                onClick={() => handleNavigation(item.path)}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: 'primary.light',
                    '&:hover': {
                      backgroundColor: 'primary.light',
                    },
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    color: location.pathname === item.path ? 'primary.main' : 'inherit',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.text}
                  sx={{
                    '& .MuiListItemText-primary': {
                      color: location.pathname === item.path ? 'primary.main' : 'inherit',
                    },
                  }}
                />
              </ListItemButton>
            </ListItem>
          </React.Fragment>
        ))}
      </List>
    </Drawer>
  );
};

export default SideNavigation;
