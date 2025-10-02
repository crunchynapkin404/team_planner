import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import { CheckCircle, Cancel, PersonAdd } from '@mui/icons-material';
import { apiClient } from '../services/apiClient';

interface PendingUser {
  id: number;
  username: string;
  email: string;
  name: string;
  date_joined: string;
}

interface PendingUsersResponse {
  success: boolean;
  pending_users: PendingUser[];
  count: number;
}

const PendingUsersPage: React.FC = () => {
  const [users, setUsers] = useState<PendingUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    action: 'approve' | 'reject' | null;
    user: PendingUser | null;
  }>({
    open: false,
    action: null,
    user: null,
  });

  useEffect(() => {
    fetchPendingUsers();
  }, []);

  const fetchPendingUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get<PendingUsersResponse>('/api/admin/pending-users/');
      setUsers(response.pending_users);
    } catch (err: any) {
      const errorMessage = err.data?.error || err.message || 'Failed to load pending users';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (userId: number) => {
    try {
      setError(null);
      setSuccess(null);
      await apiClient.post(`/api/admin/approve-user/${userId}/`);
      setSuccess('User approved successfully!');
      await fetchPendingUsers();
      handleCloseDialog();
    } catch (err: any) {
      const errorMessage = err.data?.error || err.message || 'Failed to approve user';
      setError(errorMessage);
    }
  };

  const handleReject = async (userId: number) => {
    try {
      setError(null);
      setSuccess(null);
      await apiClient.post(`/api/admin/reject-user/${userId}/`);
      setSuccess('User registration rejected and deleted.');
      await fetchPendingUsers();
      handleCloseDialog();
    } catch (err: any) {
      const errorMessage = err.data?.error || err.message || 'Failed to reject user';
      setError(errorMessage);
    }
  };

  const handleOpenDialog = (action: 'approve' | 'reject', user: PendingUser) => {
    setConfirmDialog({
      open: true,
      action,
      user,
    });
  };

  const handleCloseDialog = () => {
    setConfirmDialog({
      open: false,
      action: null,
      user: null,
    });
  };

  const handleConfirm = () => {
    if (confirmDialog.user && confirmDialog.action) {
      if (confirmDialog.action === 'approve') {
        handleApprove(confirmDialog.user.id);
      } else {
        handleReject(confirmDialog.user.id);
      }
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" alignItems="center" mb={3}>
        <PersonAdd sx={{ fontSize: 32, mr: 1 }} />
        <Typography variant="h4" component="h1">
          Pending User Registrations
        </Typography>
        <Chip
          label={users.length}
          color="primary"
          size="small"
          sx={{ ml: 2 }}
        />
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {users.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No pending user registrations
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            All user registrations have been reviewed.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell><strong>Username</strong></TableCell>
                <TableCell><strong>Full Name</strong></TableCell>
                <TableCell><strong>Email</strong></TableCell>
                <TableCell><strong>Registered</strong></TableCell>
                <TableCell align="center"><strong>Actions</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {user.username}
                    </Typography>
                  </TableCell>
                  <TableCell>{user.name}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {formatDate(user.date_joined)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Box display="flex" gap={1} justifyContent="center">
                      <Button
                        variant="contained"
                        color="success"
                        size="small"
                        startIcon={<CheckCircle />}
                        onClick={() => handleOpenDialog('approve', user)}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="outlined"
                        color="error"
                        size="small"
                        startIcon={<Cancel />}
                        onClick={() => handleOpenDialog('reject', user)}
                      >
                        Reject
                      </Button>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={handleCloseDialog}
      >
        <DialogTitle>
          {confirmDialog.action === 'approve' ? 'Approve User?' : 'Reject User?'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {confirmDialog.action === 'approve' ? (
              <>
                Are you sure you want to approve <strong>{confirmDialog.user?.username}</strong>?
                <br /><br />
                They will be able to log in immediately with Employee role permissions.
              </>
            ) : (
              <>
                Are you sure you want to reject <strong>{confirmDialog.user?.username}</strong>?
                <br /><br />
                This will permanently delete their registration. This action cannot be undone.
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            color={confirmDialog.action === 'approve' ? 'success' : 'error'}
            variant="contained"
            autoFocus
          >
            {confirmDialog.action === 'approve' ? 'Approve' : 'Reject'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PendingUsersPage;
