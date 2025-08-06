import React, { useState, useEffect } from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
  Divider,
  CircularProgress,
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import { navigationService, NavigationItem } from '../../services/navigationService';
import { userService } from '../../services/userService';

const drawerWidth = 240;

const SideNavigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [navigationItems, setNavigationItems] = useState<NavigationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUserAndNavigation = async () => {
      try {
        const currentUser = await userService.getCurrentUser();
        const items = navigationService.getNavigationItems(currentUser);
        setNavigationItems(items);
      } catch (error) {
        console.error('Failed to fetch user data:', error);
        // Set minimal navigation for unauthenticated users
        const items = navigationService.getNavigationItems(null);
        setNavigationItems(items);
      } finally {
        setLoading(false);
      }
    };

    fetchUserAndNavigation();
  }, []);

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  if (loading) {
    return (
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            top: '64px',
          },
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
          <CircularProgress />
        </Box>
      </Drawer>
    );
  }

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
                  {navigationService.getIcon(item.iconName)}
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
