import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  List,
  ListItem,
  ListItemText,
  Chip,
} from '@mui/material';
import {
  Schedule,
  People,
  SwapHoriz,
  BeachAccess,
} from '@mui/icons-material';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactElement;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color }) => {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box
            sx={{
              p: 1,
              borderRadius: 1,
              backgroundColor: `${color}.light`,
              color: `${color}.main`,
              mr: 2,
            }}
          >
            {icon}
          </Box>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </Box>
        <Typography variant="h4" component="div" color="primary">
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
};

const Dashboard: React.FC = () => {
  // Mock user for now - will be replaced with proper auth
  const user = { name: 'Developer', username: 'dev_user' };

  // Mock data - in real app, this would come from API
  const stats = [
    {
      title: 'My Shifts This Week',
      value: 5,
      icon: <Schedule />,
      color: 'primary',
    },
    {
      title: 'Active Employees',
      value: 25,
      icon: <People />,
      color: 'success',
    },
    {
      title: 'Pending Swaps',
      value: 3,
      icon: <SwapHoriz />,
      color: 'warning',
    },
    {
      title: 'Leave Requests',
      value: 7,
      icon: <BeachAccess />,
      color: 'info',
    },
  ];

  const recentActivities = [
    { text: 'John requested to swap shift on 2025-01-15', status: 'pending' },
    { text: 'Sarah\'s leave request approved', status: 'approved' },
    { text: 'New orchestration completed', status: 'info' },
    { text: 'Mike\'s swap request rejected', status: 'rejected' },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'info';
    }
  };

  return (
    <Box sx={{ width: '100%', height: '100%' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Welcome back, {user?.name || user?.username}!
      </Typography>
      
      <Grid container spacing={3} sx={{ width: '100%' }}>
        {/* Stats Cards */}
        {stats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <StatCard {...stat} />
          </Grid>
        ))}
        
        {/* Recent Activities */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '400px' }}>
            <Typography variant="h6" gutterBottom>
              Recent Activities
            </Typography>
            <List>
              {recentActivities.map((activity, index) => (
                <ListItem key={index} divider>
                  <ListItemText
                    primary={activity.text}
                    secondary={
                      <Chip
                        label={activity.status}
                        color={getStatusColor(activity.status) as any}
                        size="small"
                        sx={{ mt: 1 }}
                      />
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
        
        {/* Quick Actions */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '400px' }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Card sx={{ cursor: 'pointer' }}>
                <CardContent>
                  <Typography variant="h6" color="primary">
                    Request Shift Swap
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Request to swap your shift with a colleague
                  </Typography>
                </CardContent>
              </Card>
              <Card sx={{ cursor: 'pointer' }}>
                <CardContent>
                  <Typography variant="h6" color="primary">
                    Apply for Leave
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Submit a new leave request
                  </Typography>
                </CardContent>
              </Card>
              <Card sx={{ cursor: 'pointer' }}>
                <CardContent>
                  <Typography variant="h6" color="primary">
                    View Schedule
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Check your upcoming shifts
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
