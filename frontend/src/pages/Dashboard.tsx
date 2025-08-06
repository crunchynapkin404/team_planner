import React, { useEffect, useState } from 'react';
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
  CircularProgress,
  Alert,
  Button,
} from '@mui/material';
import {
  Security,
  Support,
  PhoneInTalk,
  People,
  Schedule,
  SwapHoriz,
  Notifications,
} from '@mui/icons-material';
import { dashboardService, DashboardData, Engineer } from '../services/dashboardService';
import { userService, UserDashboardData, UserShift } from '../services/userService';
import { formatDate, formatDateTime } from '../utils/dateUtils';

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
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {title}
          </Typography>
        </Box>
        <Typography 
          variant={typeof value === 'string' ? 'h6' : 'h4'} 
          component="div" 
          color="primary"
          sx={{ 
            wordBreak: 'break-word',
            fontWeight: typeof value === 'string' ? 'normal' : 'bold'
          }}
        >
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
};

const Dashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [userDashboardData, setUserDashboardData] = useState<UserDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        // Load general dashboard data (required)
        const generalData = await dashboardService.getDashboardData();
        setDashboardData(generalData);
        
        // Try to load user-specific dashboard data (optional)
        try {
          const userData = await userService.getUserDashboardData();
          setUserDashboardData(userData);
        } catch (userDataError) {
          console.warn('User dashboard data not available:', userDataError);
          // Set default empty user data
          setUserDashboardData({
            upcoming_shifts: [],
            incoming_swap_requests: [],
            outgoing_swap_requests: [],
            recent_activities: [],
            shift_stats: {
              total_shifts_this_month: 0,
              completed_shifts: 0,
              upcoming_shifts: 0,
              swap_requests_pending: 0,
            },
          });
        }
        
        setError(null);
      } catch (err) {
        setError('Failed to fetch dashboard data');
        console.error('Dashboard fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const formatEngineerName = (engineer: Engineer | null | undefined): string => {
    if (!engineer) return 'None assigned';
    return engineer.name || engineer.username;
  };

  const todayStats = [
    {
      title: 'Incident Engineer of Today',
      value: formatEngineerName(dashboardData?.incident_engineer),
      icon: <Security />,
      color: 'error',
    },
    {
      title: 'Incident-Standby Engineer of Today',
      value: formatEngineerName(dashboardData?.incident_standby_engineer),
      icon: <Support />,
      color: 'warning',
    },
    {
      title: 'Waakdienst Engineer of Today',
      value: formatEngineerName(dashboardData?.waakdienst_engineer),
      icon: <PhoneInTalk />,
      color: 'primary',
    },
    {
      title: 'Engineers Working Today',
      value: dashboardData?.engineers_working_count && dashboardData?.available_engineers 
        ? `${dashboardData.engineers_working_count}/${dashboardData.available_engineers} Engineers working today`
        : dashboardData?.engineers_working?.length || 0,
      icon: <People />,
      color: 'success',
    },
  ];

  const recentActivities = userDashboardData?.recent_activities || [];
  const upcomingShifts = userDashboardData?.upcoming_shifts || [];
  const incomingSwapRequests = userDashboardData?.incoming_swap_requests || [];
  const shiftStats = userDashboardData?.shift_stats;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'pending':
        return 'warning';
      case 'completed':
        return 'info';
      default:
        return 'default';
    }
  };

  const formatShiftTime = (shift: UserShift | { start_time: string; end_time: string; title?: string } | null | undefined) => {
    if (!shift || !shift.start_time || !shift.end_time) {
      return 'Time not available';
    }
    
    const start = new Date(shift.start_time);
    const end = new Date(shift.end_time);
    return `${formatDate(start)} ${formatDateTime(start).split(' ')[1]} - ${formatDateTime(end).split(' ')[1]}`;
  };

  const handleSwapResponse = async (requestId: number, action: 'approve' | 'reject') => {
    try {
      await userService.respondToSwapRequest(requestId, action);
      // Refresh dashboard data
      const userData = await userService.getUserDashboardData();
      setUserDashboardData(userData);
    } catch (err) {
      console.error('Failed to respond to swap request:', err);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ width: '100%', minHeight: '100%' }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', minHeight: '100%' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Welcome to your Dashboard!
      </Typography>
      
      <Grid container spacing={3} sx={{ width: '100%' }}>
        {/* Today's Shift Cards */}
        {todayStats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <StatCard {...stat} />
          </Grid>
        ))}
        
        {/* Recent Activities */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '400px', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              Recent Activities
            </Typography>
            {recentActivities.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No recent activities
              </Typography>
            ) : (
              <List>
                {recentActivities.map((activity, index) => (
                  <ListItem key={activity.id || index} divider>
                    <ListItemText
                      primary={activity.message}
                      secondary={
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                          <Chip
                            label={activity.status}
                            color={getStatusColor(activity.status) as any}
                            size="small"
                          />
                          <Typography variant="caption" color="text.secondary">
                            {formatDate(new Date(activity.created_at))}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Upcoming Shifts */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '400px', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Schedule />
              Your Upcoming Shifts
            </Typography>
            {upcomingShifts.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No upcoming shifts scheduled
              </Typography>
            ) : (
              <List>
                {upcomingShifts.map((shift) => {
                  // Defensive check to ensure shift has valid data
                  if (!shift || !shift.id) {
                    return null;
                  }
                  
                  return (
                    <ListItem key={shift.id} divider>
                      <ListItemText
                        primary={shift.title || 'Untitled shift'}
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              {formatShiftTime(shift)}
                            </Typography>
                            <Chip
                              label={shift.shift_type || 'Unknown'}
                              color="primary"
                              size="small"
                              sx={{ mt: 0.5 }}
                            />
                          </Box>
                        }
                      />
                    </ListItem>
                  );
                }).filter(Boolean)}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Incoming Swap Requests */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '400px', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SwapHoriz />
              Incoming Swap Requests
            </Typography>
            {incomingSwapRequests.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No pending swap requests
              </Typography>
            ) : (
              <List>
                {incomingSwapRequests.map((request) => {
                  // Defensive check to ensure request has valid data
                  if (!request || !request.id) {
                    return null;
                  }
                  
                  return (
                    <ListItem key={request.id} divider>
                      <ListItemText
                        primary={`${request.requester?.first_name || request.requester?.username || 'Unknown user'} wants to swap`}
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              Their shift: {formatShiftTime(request.requesting_shift)}
                            </Typography>
                            {request.target_shift && (
                              <Typography variant="body2">
                                Your shift: {formatShiftTime(request.target_shift)}
                              </Typography>
                            )}
                            {request.reason && (
                              <Typography variant="body2" style={{ fontStyle: 'italic' }}>
                                "{request.reason}"
                              </Typography>
                            )}
                            <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                              <Button
                                size="small"
                                color="success"
                                onClick={() => handleSwapResponse(request.id, 'approve')}
                              >
                                Approve
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                onClick={() => handleSwapResponse(request.id, 'reject')}
                              >
                                Reject
                              </Button>
                            </Box>
                          </Box>
                        }
                      />
                    </ListItem>
                  );
                }).filter(Boolean)}
              </List>
            )}
          </Paper>
        </Grid>

        {/* User Statistics */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '400px', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Notifications />
              Your Stats This Month
            </Typography>
            {shiftStats ? (
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Card sx={{ textAlign: 'center', p: 2 }}>
                    <Typography variant="h4" color="primary">
                      {shiftStats.total_shifts_this_month}
                    </Typography>
                    <Typography variant="body2">
                      Total Shifts
                    </Typography>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card sx={{ textAlign: 'center', p: 2 }}>
                    <Typography variant="h4" color="success.main">
                      {shiftStats.completed_shifts}
                    </Typography>
                    <Typography variant="body2">
                      Completed
                    </Typography>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card sx={{ textAlign: 'center', p: 2 }}>
                    <Typography variant="h4" color="info.main">
                      {shiftStats.upcoming_shifts}
                    </Typography>
                    <Typography variant="body2">
                      Upcoming
                    </Typography>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card sx={{ textAlign: 'center', p: 2 }}>
                    <Typography variant="h4" color="warning.main">
                      {shiftStats.swap_requests_pending}
                    </Typography>
                    <Typography variant="body2">
                      Pending Swaps
                    </Typography>
                  </Card>
                </Grid>
              </Grid>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Statistics not available
              </Typography>
            )}
          </Paper>
        </Grid>
        
        {/* Quick Actions */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '400px', overflow: 'auto' }}>
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
