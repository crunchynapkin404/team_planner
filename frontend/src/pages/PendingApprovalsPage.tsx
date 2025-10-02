import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Stack,
  Card,
  CardContent,
  Badge,
  IconButton,
  Stepper,
  Step,
  StepLabel,
  List,
  ListItem,
  ListItemText,
  Divider,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  Visibility as ViewIcon,
  SwapHoriz as SwapIcon,
  Person as PersonIcon,
  Schedule as ScheduleIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import swapApprovalService, {
  type PendingApproval,
  type ApprovalChain,
  type AuditTrailEntry,
} from '../services/swapApprovalService';

const PendingApprovalsPage: React.FC = () => {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Dialog states
  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState<PendingApproval | null>(null);
  const [approvalChain, setApprovalChain] = useState<ApprovalChain | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditTrailEntry[]>([]);
  
  // Form states
  const [approveComments, setApproveComments] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    fetchPendingApprovals();
  }, []);

  const fetchPendingApprovals = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await swapApprovalService.getPendingApprovals();
      setApprovals(data);
    } catch (err) {
      setError('Failed to load pending approvals');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDetails = async (approval: PendingApproval) => {
    try {
      setSelectedApproval(approval);
      setDetailsDialogOpen(true);
      
      // Fetch approval chain and audit trail
      const [chain, trail] = await Promise.all([
        swapApprovalService.getApprovalChain(approval.swap_request_id),
        swapApprovalService.getAuditTrail(approval.swap_request_id),
      ]);
      
      setApprovalChain(chain);
      setAuditTrail(trail);
    } catch (err) {
      setError('Failed to load swap details');
      console.error(err);
    }
  };

  const handleOpenApprove = (approval: PendingApproval) => {
    setSelectedApproval(approval);
    setApproveComments('');
    setApproveDialogOpen(true);
  };

  const handleOpenReject = (approval: PendingApproval) => {
    setSelectedApproval(approval);
    setRejectReason('');
    setRejectDialogOpen(true);
  };

  const handleApprove = async () => {
    if (!selectedApproval) return;

    try {
      setActionLoading(true);
      await swapApprovalService.approveSwap(selectedApproval.swap_request_id, {
        comments: approveComments || undefined,
      });
      
      setSuccess('Swap request approved successfully');
      setApproveDialogOpen(false);
      setSelectedApproval(null);
      await fetchPendingApprovals();
    } catch (err) {
      setError('Failed to approve swap request');
      console.error(err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedApproval || !rejectReason) return;

    try {
      setActionLoading(true);
      await swapApprovalService.rejectSwap(selectedApproval.swap_request_id, {
        reason: rejectReason,
      });
      
      setSuccess('Swap request rejected');
      setRejectDialogOpen(false);
      setSelectedApproval(null);
      await fetchPendingApprovals();
    } catch (err) {
      setError('Failed to reject swap request');
      console.error(err);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          <SwapIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Pending Approvals
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Review and approve swap requests awaiting your approval
        </Typography>
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

      {/* Summary Cards */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="caption">
              Pending Your Approval
            </Typography>
            <Typography variant="h4">{approvals.length}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="caption">
              Delegated to You
            </Typography>
            <Typography variant="h4">
              {approvals.filter(a => a.is_delegated).length}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="caption">
              Multi-Level Approvals
            </Typography>
            <Typography variant="h4">
              {approvals.filter(a => a.total_levels > 1).length}
            </Typography>
          </CardContent>
        </Card>
      </Stack>

      {/* Approvals Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Requested By</TableCell>
              <TableCell>Swap With</TableCell>
              <TableCell>Shift Details</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Approval Progress</TableCell>
              <TableCell>Requested</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {approvals.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 8 }}>
                  <Typography color="text.secondary">
                    No pending approvals at this time
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              approvals.map((approval) => (
                <TableRow key={approval.id} hover>
                  <TableCell>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <PersonIcon fontSize="small" color="action" />
                      <Typography>{approval.requesting_employee}</Typography>
                    </Stack>
                    {approval.is_delegated && (
                      <Chip
                        label={`Delegated from ${approval.delegated_from}`}
                        size="small"
                        color="info"
                        sx={{ mt: 0.5 }}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <PersonIcon fontSize="small" color="action" />
                      <Typography>{approval.target_employee}</Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Stack spacing={0.5}>
                      <Typography variant="body2">
                        {format(new Date(approval.requesting_shift_date), 'MMM d, yyyy')}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {approval.requesting_shift_time}
                      </Typography>
                      {approval.target_shift_date && (
                        <>
                          <SwapIcon fontSize="small" color="action" />
                          <Typography variant="body2">
                            {format(new Date(approval.target_shift_date), 'MMM d, yyyy')}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {approval.target_shift_time}
                          </Typography>
                        </>
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={approval.shift_type}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="body2">
                        Level {approval.current_level} of {approval.total_levels}
                      </Typography>
                      <Chip
                        label={`${approval.current_level}/${approval.total_levels}`}
                        size="small"
                        color={approval.current_level === approval.total_levels ? 'success' : 'warning'}
                      />
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {format(new Date(approval.requested_date), 'MMM d, HH:mm')}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5}>
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDetails(approval)}
                        >
                          <ViewIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Approve">
                        <IconButton
                          size="small"
                          color="success"
                          onClick={() => handleOpenApprove(approval)}
                        >
                          <ApproveIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Reject">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleOpenReject(approval)}
                        >
                          <RejectIcon />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Approve Dialog */}
      <Dialog open={approveDialogOpen} onClose={() => setApproveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Approve Swap Request</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" gutterBottom>
              You are about to approve a swap request from{' '}
              <strong>{selectedApproval?.requesting_employee}</strong>.
            </Typography>
            <TextField
              label="Comments (Optional)"
              value={approveComments}
              onChange={(e) => setApproveComments(e.target.value)}
              multiline
              rows={3}
              fullWidth
              sx={{ mt: 2 }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApproveDialogOpen(false)} disabled={actionLoading}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="success"
            onClick={handleApprove}
            disabled={actionLoading}
            startIcon={actionLoading ? <CircularProgress size={16} /> : <ApproveIcon />}
          >
            Approve
          </Button>
        </DialogActions>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onClose={() => setRejectDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Reject Swap Request</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" gutterBottom>
              You are about to reject a swap request from{' '}
              <strong>{selectedApproval?.requesting_employee}</strong>.
            </Typography>
            <TextField
              label="Reason for Rejection *"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              multiline
              rows={3}
              required
              fullWidth
              sx={{ mt: 2 }}
              error={!rejectReason}
              helperText={!rejectReason ? 'Reason is required' : ''}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectDialogOpen(false)} disabled={actionLoading}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleReject}
            disabled={actionLoading || !rejectReason}
            startIcon={actionLoading ? <CircularProgress size={16} /> : <RejectIcon />}
          >
            Reject
          </Button>
        </DialogActions>
      </Dialog>

      {/* Details Dialog */}
      <Dialog open={detailsDialogOpen} onClose={() => setDetailsDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Swap Request Details</DialogTitle>
        <DialogContent>
          {approvalChain && (
            <Box sx={{ pt: 2 }}>
              {/* Approval Chain Stepper */}
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Approval Chain
              </Typography>
              <Stepper activeStep={approvalChain.current_level - 1} sx={{ mb: 3 }}>
                {approvalChain.steps.map((step, index) => (
                  <Step key={step.id} completed={step.status === 'approved'}>
                    <StepLabel
                      error={step.status === 'rejected'}
                      optional={
                        <Typography variant="caption">
                          {step.approver_name}
                          {step.status === 'approved' && step.approved_at && (
                            <> • {format(new Date(step.approved_at), 'MMM d, HH:mm')}</>
                          )}
                        </Typography>
                      }
                    >
                      Level {step.level}
                    </StepLabel>
                  </Step>
                ))}
              </Stepper>

              {approvalChain.can_auto_approve && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="body2" fontWeight="bold">
                    Auto-Approval Available
                  </Typography>
                  <Typography variant="caption">
                    {approvalChain.auto_approve_reason}
                  </Typography>
                </Alert>
              )}

              <Divider sx={{ my: 2 }} />

              {/* Audit Trail */}
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Audit Trail
              </Typography>
              <List dense>
                {auditTrail.map((entry) => (
                  <ListItem key={entry.id}>
                    <ListItemText
                      primary={
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Chip
                            label={entry.action}
                            size="small"
                            color={
                              entry.action === 'approved' || entry.action === 'auto_approved'
                                ? 'success'
                                : entry.action === 'rejected'
                                ? 'error'
                                : 'default'
                            }
                          />
                          <Typography variant="body2">
                            by <strong>{entry.performed_by_name}</strong>
                          </Typography>
                        </Stack>
                      }
                      secondary={
                        <>
                          <Typography variant="caption" color="text.secondary">
                            {format(new Date(entry.timestamp), 'MMM d, yyyy HH:mm:ss')}
                          </Typography>
                          {entry.comments && (
                            <Typography variant="body2" sx={{ mt: 0.5 }}>
                              {entry.comments}
                            </Typography>
                          )}
                        </>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PendingApprovalsPage;
