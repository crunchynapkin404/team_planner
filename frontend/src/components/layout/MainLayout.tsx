import React from 'react';
import { Box } from '@mui/material';
import TopNavigation from './TopNavigation';
import SideNavigation from './SideNavigation';

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <TopNavigation />
      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <SideNavigation />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            backgroundColor: 'background.default',
            overflow: 'auto',
            height: 'calc(100vh - 64px)', // Account for top navigation height
            maxHeight: 'calc(100vh - 64px)',
            p: 3,
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
};

export default MainLayout;
