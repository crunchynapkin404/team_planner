import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Chip,
  Pagination,
  CircularProgress,
  Button,
  Divider,
  Alert,
} from '@mui/material';
import {
  Circle as CircleIcon,
  CheckCircle as CheckCircleIcon,
  MarkEmailRead as MarkEmailReadIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { notificationService, Notification } from '../services/notificationService';

// Helper function to format relative time
const formatTimeAgo = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 4) return `${weeks}w ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
};

// Helper function to get notification type label
const getNotificationTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    shift_assigned: 'Shift Assigned',
    shift_changed: 'Shift Changed',
    shift_cancelled: 'Shift Cancelled',
    shift_reminder: 'Shift Reminder',
    swap_requested: 'Swap Requested',
    swap_approved: 'Swap Approved',
    swap_rejected: 'Swap Rejected',
    leave_approved: 'Leave Approved',
    leave_rejected: 'Leave Rejected',
    leave_cancelled: 'Leave Cancelled',
    schedule_published: 'Schedule Published',
  };
  return labels[type] || type;
};

// Helper function to get notification type color
const getNotificationTypeColor = (type: string): 'success' | 'error' | 'warning' | 'info' | 'default' => {
  if (type.includes('approved')) return 'success';
  if (type.includes('rejected') || type.includes('cancelled')) return 'error';
  if (type.includes('reminder') || type.includes('requested')) return 'warning';
  return 'info';
};

const NotificationList: React.FC = () => {
  const navigate = useNavigate();
  const [tab, setTab] = useState(0); // 0 = All, 1 = Unread
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = async (currentPage: number, isRead?: boolean) => {
    try {
      setLoading(true);
      setError(null);
      const params: any = { page: currentPage };
      if (isRead !== undefined) {
        params.is_read = isRead;
      }
      const response = await notificationService.listNotifications(params);
      setNotifications(response.results);
      setTotalPages(Math.ceil(response.count / 10)); // Assuming 10 items per page
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
      setError('Failed to load notifications. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const isRead = tab === 1 ? false : undefined; // Tab 1 = Unread only
    fetchNotifications(page, isRead);
  }, [page, tab]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTab(newValue);
    setPage(1); // Reset to first page when changing tabs
  };

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleMarkAsRead = async (notification: Notification) => {
    try {
      if (!notification.is_read) {
        await notificationService.markAsRead(notification.id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n))
        );
      }
      // Navigate to action URL if available
      if (notification.action_url) {
        navigate(notification.action_url);
      }
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const handleMarkAsUnread = async (id: number) => {
    try {
      await notificationService.markAsUnread(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: false } : n))
      );
    } catch (err) {
      console.error('Failed to mark notification as unread:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationService.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      console.error('Failed to mark all notifications as read:', err);
      setError('Failed to mark all as read. Please try again.');
    }
  };

  const handleRefresh = () => {
    const isRead = tab === 1 ? false : undefined;
    fetchNotifications(page, isRead);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1">
            Notifications
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={loading}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<MarkEmailReadIcon />}
              onClick={handleMarkAllRead}
              disabled={loading || notifications.length === 0}
            >
              Mark All as Read
            </Button>
          </Box>
        </Box>

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Tabs */}
        <Tabs value={tab} onChange={handleTabChange} sx={{ mb: 2 }}>
          <Tab label="All Notifications" />
          <Tab label="Unread" />
        </Tabs>

        <Divider sx={{ mb: 2 }} />

        {/* Loading State */}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Empty State */}
        {!loading && notifications.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="h6" color="text.secondary">
              {tab === 1 ? 'No unread notifications' : 'No notifications'}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {tab === 1
                ? 'All caught up! You have no unread notifications.'
                : 'You will see notifications here when actions occur.'}
            </Typography>
          </Box>
        )}

        {/* Notifications List */}
        {!loading && notifications.length > 0 && (
          <List>
            {notifications.map((notification, index) => (
              <React.Fragment key={notification.id}>
                {index > 0 && <Divider />}
                <ListItem
                  sx={{
                    backgroundColor: !notification.is_read ? 'action.hover' : 'transparent',
                    borderLeft: !notification.is_read ? 3 : 0,
                    borderColor: 'primary.main',
                    '&:hover': {
                      backgroundColor: 'action.selected',
                    },
                    cursor: notification.action_url ? 'pointer' : 'default',
                    py: 2,
                  }}
                  onClick={() => handleMarkAsRead(notification)}
                  secondaryAction={
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <IconButton
                        edge="end"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (notification.is_read) {
                            handleMarkAsUnread(notification.id);
                          } else {
                            notificationService.markAsRead(notification.id);
                            setNotifications((prev) =>
                              prev.map((n) =>
                                n.id === notification.id ? { ...n, is_read: true } : n
                              )
                            );
                          }
                        }}
                        title={notification.is_read ? 'Mark as unread' : 'Mark as read'}
                      >
                        {notification.is_read ? <CircleIcon /> : <CheckCircleIcon />}
                      </IconButton>
                    </Box>
                  }
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    {notification.is_read ? (
                      <CheckCircleIcon color="success" />
                    ) : (
                      <CircleIcon color="primary" sx={{ fontSize: 12 }} />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Typography
                          variant="subtitle1"
                          sx={{
                            fontWeight: notification.is_read ? 'normal' : 'bold',
                          }}
                        >
                          {notification.title}
                        </Typography>
                        <Chip
                          label={getNotificationTypeLabel(notification.notification_type)}
                          size="small"
                          color={getNotificationTypeColor(notification.notification_type)}
                          sx={{ height: 20, fontSize: '0.7rem' }}
                        />
                      </Box>
                    }
                    secondary={
                      <>
                        <Typography
                          component="span"
                          variant="body2"
                          color="text.primary"
                          sx={{ display: 'block', mb: 0.5 }}
                        >
                          {notification.message}
                        </Typography>
                        <Typography component="span" variant="caption" color="text.secondary">
                          {formatTimeAgo(notification.created)}
                        </Typography>
                      </>
                    }
                  />
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        )}

        {/* Pagination */}
        {!loading && totalPages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
            <Pagination
              count={totalPages}
              page={page}
              onChange={handlePageChange}
              color="primary"
              showFirstButton
              showLastButton
            />
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default NotificationList;
