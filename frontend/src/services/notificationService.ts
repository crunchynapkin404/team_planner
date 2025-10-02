import { apiClient } from './apiClient';

export interface Notification {
  id: number;
  notification_type: string;
  title: string;
  message: string;
  related_shift_id?: number;
  related_leave_id?: number;
  related_swap_id?: number;
  data: Record<string, any>;
  is_read: boolean;
  read_at?: string;
  action_url: string;
  created: string;
}

export interface NotificationPreference {
  id: number;
  user: number;
  // Email preferences
  email_shift_assigned: boolean;
  email_shift_updated: boolean;
  email_shift_cancelled: boolean;
  email_swap_requested: boolean;
  email_swap_approved: boolean;
  email_swap_rejected: boolean;
  email_leave_approved: boolean;
  email_leave_rejected: boolean;
  email_schedule_published: boolean;
  email_reminders: boolean;
  // In-app preferences
  inapp_shift_assigned: boolean;
  inapp_shift_updated: boolean;
  inapp_shift_cancelled: boolean;
  inapp_swap_requested: boolean;
  inapp_swap_approved: boolean;
  inapp_swap_rejected: boolean;
  inapp_leave_approved: boolean;
  inapp_leave_rejected: boolean;
  inapp_schedule_published: boolean;
  inapp_reminders: boolean;
  // Timing
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  created: string;
  modified: string;
}

export interface NotificationListResponse {
  count: number;
  total_pages: number;
  current_page: number;
  has_next: boolean;
  has_previous: boolean;
  results: Notification[];
}

export const notificationService = {
  /**
   * Get count of unread notifications
   */
  getUnreadCount: async (): Promise<{ unread_count: number }> => {
    const response: any = await apiClient.get('/notifications/unread_count/');
    return response;
  },

  // List notifications
  /**
   * Get list of notifications with optional filtering
   */
  listNotifications: async (params?: {
    is_read?: boolean;
    notification_type?: string;
    page?: number;
  }): Promise<NotificationListResponse> => {
    const response: any = await apiClient.get('/notifications/', { params });
    return response;
  },

  // Get notification detail
  /**
   * Get a single notification by ID
   */
  getNotification: async (id: number): Promise<Notification> => {
    const response: any = await apiClient.get(`/notifications/${id}/`);
    return response;
  },

  // Mark notification as read
  markAsRead: async (id: number): Promise<void> => {
    await apiClient.post(`/notifications/${id}/mark_read/`);
  },

  // Mark notification as unread
  markAsUnread: async (id: number): Promise<void> => {
    await apiClient.post(`/notifications/${id}/mark_unread/`);
  },

  /**
   * Mark all notifications as read
   */
  markAllRead: async (): Promise<{ message: string; updated_count: number }> => {
    const response: any = await apiClient.post('/notifications/mark_all_read/');
    return response;
  },

  // Clear all notifications
  clearAll: async (): Promise<{ count: number }> => {
    const response: any = await apiClient.delete('/notifications/clear_all/');
    return response;
  },

  // Get user preferences
  getPreferences: async (): Promise<NotificationPreference> => {
    const response: any = await apiClient.get('/notification-preferences/my_preferences/');
    return response;
  },

  // Update user preferences
  updatePreferences: async (
    preferences: Partial<NotificationPreference>
  ): Promise<NotificationPreference> => {
    const response: any = await apiClient.patch(
      '/notification-preferences/update_preferences/',
      preferences
    );
    return response;
  },
};
