import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Pagination,
  Alert,
  AlertTitle,
  CircularProgress,
  Tooltip,
  Stack,
  Fab,
  FormHelperText,
  Paper,
} from '@mui/material';
import {
  Add as AddIcon,
  Visibility as ViewIcon,
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  Block as CancelIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon,
  Search as SearchIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import {
  leaveService,
  LeaveRequest,
  LeaveType,
  LeaveRequestFilters,
  LeaveStats,
  CreateLeaveRequestData,
} from '../services/leaveService';
import { formatDate, formatDateTime } from '../utils/dateUtils';

const LeaveRequestPage: React.FC = () => {
  const { user } = useSelector((state: RootState) => state.auth) as { user: any };
  
  // State management
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([]);
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const [stats, setStats] = useState<LeaveStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  
  // Filters
  const [filters, setFilters] = useState<LeaveRequestFilters>({
    page_size: 20,
  });
  const [showFilters, setShowFilters] = useState(false);
  
  // Dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedLeaveRequest, setSelectedLeaveRequest] = useState<LeaveRequest | null>(null);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [conflictsDialogOpen, setConflictsDialogOpen] = useState(false);
  const [conflictingShifts, setConflictingShifts] = useState<any[]>([]);
  const [loadingConflicts, setLoadingConflicts] = useState(false);

  // Create form state
  const [createForm, setCreateForm] = useState({
    leave_type_id: '',
    start_date: '',
    end_date: '',
    days_requested: 1,
    reason: '',
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Load initial data
  useEffect(() => {
    loadData();
  }, [filters, currentPage]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load leave requests
      const requestFilters = { ...filters, page: currentPage };
      console.log('Request filters:', requestFilters);
      console.log('Current user:', user);
      const requestsResponse = await leaveService.getLeaveRequests(requestFilters);
      console.log('Leave requests response:', requestsResponse);
      console.log('Number of requests:', requestsResponse.results?.length);
      console.log('Results array:', requestsResponse.results);
      setLeaveRequests(requestsResponse.results || []);
      setTotalPages(requestsResponse.total_pages || 1);
      setTotalCount(requestsResponse.count || 0);

      // Load leave types if not already loaded
      if (leaveTypes.length === 0) {
        const typesResponse = await leaveService.getLeaveTypes();
        setLeaveTypes(Array.isArray(typesResponse) ? typesResponse : []);
      }

      // Load user stats
      const statsResponse = await leaveService.getUserStats();
      setStats(statsResponse);
    } catch (err) {
      setError('Failed to load leave requests. Please try again.');
      console.error('Error loading leave data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: keyof LeaveRequestFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
    }));
    setCurrentPage(1); // Reset to first page when filters change
  };

  const clearFilters = () => {
    setFilters({ page_size: 20 });
    setCurrentPage(1);
  };

  const handleViewDetails = (leaveRequest: LeaveRequest) => {
    setSelectedLeaveRequest(leaveRequest);
    setDetailDialogOpen(true);
  };

  const handleApprove = async (id: number) => {
    try {
      await leaveService.approveLeaveRequest(id);
      loadData(); // Refresh the list
    } catch (err) {
      setError('Failed to approve leave request.');
      console.error('Error approving leave request:', err);
    }
  };

  const handleReject = async () => {
    if (!selectedLeaveRequest) return;
    
    try {
      await leaveService.rejectLeaveRequest(selectedLeaveRequest.id, rejectionReason);
      setRejectDialogOpen(false);
      setRejectionReason('');
      setSelectedLeaveRequest(null);
      loadData(); // Refresh the list
    } catch (err) {
      setError('Failed to reject leave request.');
      console.error('Error rejecting leave request:', err);
    }
  };

  const handleCancel = async (id: number) => {
    try {
      await leaveService.cancelLeaveRequest(id);
      loadData(); // Refresh the list
    } catch (err) {
      setError('Failed to cancel leave request.');
      console.error('Error cancelling leave request:', err);
    }
  };

  const handleCreateFormChange = (field: string, value: any) => {
    setCreateForm(prev => ({
      ...prev,
      [field]: value,
    }));

    // Auto-calculate days when dates change
    if (field === 'start_date' || field === 'end_date') {
      const startDate = field === 'start_date' ? value : createForm.start_date;
      const endDate = field === 'end_date' ? value : createForm.end_date;
      
      if (startDate && endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        const timeDiff = end.getTime() - start.getTime();
        const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24)) + 1; // +1 to include both start and end dates
        
        if (daysDiff > 0) {
          setCreateForm(prev => ({
            ...prev,
            [field]: value,
            days_requested: daysDiff,
          }));
        }
      }
    }
  };

  const handleCreateSubmit = async () => {
    try {
      setCreateLoading(true);
      setCreateError(null);

      // Validate form
      if (!createForm.leave_type_id || !createForm.start_date || !createForm.end_date) {
        setCreateError('Please fill in all required fields.');
        return;
      }

      if (new Date(createForm.end_date) < new Date(createForm.start_date)) {
        setCreateError('End date must be after start date.');
        return;
      }

      const formData: CreateLeaveRequestData = {
        leave_type_id: parseInt(createForm.leave_type_id),
        start_date: createForm.start_date,
        end_date: createForm.end_date,
        days_requested: createForm.days_requested,
        reason: createForm.reason,
      };

      const response = await leaveService.createLeaveRequest(formData);
      
      // Reset form and close dialog
      setCreateForm({
        leave_type_id: '',
        start_date: '',
        end_date: '',
        days_requested: 1,
        reason: '',
      });
      setCreateDialogOpen(false);
      setCreateError(null);

      // Show success message if there are conflicts
      if (response.has_conflicts) {
        setError(`Leave request created successfully! ${response.conflict_warning}`);
      }

      // Refresh the data
      loadData();
    } catch (err: any) {
      setCreateError(err?.response?.data?.detail || err?.message || 'Failed to create leave request.');
      console.error('Error creating leave request:', err);
    } finally {
      setCreateLoading(false);
    }
  };

  const handleCreateDialogClose = () => {
    setCreateDialogOpen(false);
    setCreateError(null);
    setCreateForm({
      leave_type_id: '',
      start_date: '',
      end_date: '',
      days_requested: 1,
      reason: '',
    });
  };

  const handleShowConflicts = async (leaveRequest: LeaveRequest) => {
    try {
      setLoadingConflicts(true);
      setSelectedLeaveRequest(leaveRequest);
      const conflictsResponse = await leaveService.getConflictingShifts(leaveRequest.id);
      setConflictingShifts(conflictsResponse.conflicting_shifts);
      setConflictsDialogOpen(true);
    } catch (err) {
      console.error('Error loading conflicting shifts:', err);
      setError('Failed to load conflicting shifts.');
    } finally {
      setLoadingConflicts(false);
    }
  };

  const canApprove = (leaveRequest: LeaveRequest): boolean => {
    return (
      user?.permissions?.includes('leaves.change_leaverequest') ||
      user?.is_staff ||
      false
    ) && leaveRequest.status === 'pending';
  };

  const canCancel = (leaveRequest: LeaveRequest): boolean => {
    return leaveRequest.employee.id === user?.id && leaveRequest.status === 'pending';
  };

  const getStatusChip = (status: string) => {
    return (
      <Chip
        label={status.charAt(0).toUpperCase() + status.slice(1)}
        color={
          status === 'approved' ? 'success' :
          status === 'rejected' ? 'error' :
          status === 'cancelled' ? 'default' :
          'warning'
        }
        size="small"
        variant="filled"
      />
    );
  };

  if (loading && leaveRequests?.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header with stats */}
      <Box mb={3}>
        <Typography variant="h4" gutterBottom>
          Leave Requests
        </Typography>
        
        {stats && (
          <Grid container spacing={2} mb={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Total Requests
                  </Typography>
                  <Typography variant="h4">
                    {stats.total_requests}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Pending
                  </Typography>
                  <Typography variant="h4" color="warning.main">
                    {stats.pending_requests}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Approved
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {stats.approved_requests}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Days Used ({stats.current_year})
                  </Typography>
                  <Typography variant="h4">
                    {stats.days_used_this_year}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
      </Box>

      {/* Error display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Filters */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Filters
            </Typography>
            <Button
              startIcon={<FilterIcon />}
              onClick={() => setShowFilters(!showFilters)}
            >
              {showFilters ? 'Hide' : 'Show'} Filters
            </Button>
          </Box>
          
          {showFilters && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Leave Type</InputLabel>
                  <Select
                    value={filters.leave_type_id || ''}
                    label="Leave Type"
                    onChange={(e) => handleFilterChange('leave_type_id', e.target.value || undefined)}
                  >
                    <MenuItem value="">All Types</MenuItem>
                    {leaveTypes.map((type) => (
                      <MenuItem key={type.id} value={type.id}>
                        {type.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={filters.status || ''}
                    label="Status"
                    onChange={(e) => handleFilterChange('status', e.target.value || undefined)}
                  >
                    <MenuItem value="">All Statuses</MenuItem>
                    <MenuItem value="pending">Pending</MenuItem>
                    <MenuItem value="approved">Approved</MenuItem>
                    <MenuItem value="rejected">Rejected</MenuItem>
                    <MenuItem value="cancelled">Cancelled</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  size="small"
                  label="Start Date From"
                  type="date"
                  value={filters.start_date_from || ''}
                  onChange={(e) => handleFilterChange('start_date_from', e.target.value || undefined)}
                  InputLabelProps={{
                    shrink: true,
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  size="small"
                  label="Start Date To"
                  type="date"
                  value={filters.start_date_to || ''}
                  onChange={(e) => handleFilterChange('start_date_to', e.target.value || undefined)}
                  InputLabelProps={{
                    shrink: true,
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sm={8} md={6}>
                <TextField
                  fullWidth
                  size="small"
                  label="Search"
                  placeholder="Search by employee name, reason..."
                  value={filters.search || ''}
                  onChange={(e) => handleFilterChange('search', e.target.value || undefined)}
                  InputProps={{
                    startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sm={4} md={6}>
                <Box display="flex" gap={1}>
                  <Button
                    variant="outlined"
                    startIcon={<ClearIcon />}
                    onClick={clearFilters}
                    size="small"
                  >
                    Clear Filters
                  </Button>
                </Box>
              </Grid>
            </Grid>
          )}
        </CardContent>
      </Card>

      {/* Leave Requests Table */}
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Leave Requests ({totalCount})
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              Request Leave
            </Button>
          </Box>
          
          {leaveRequests?.length === 0 && !loading ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No leave requests found. {totalCount > 0 ? 'Try adjusting your filters.' : 'Create your first leave request!'}
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Employee</TableCell>
                    <TableCell>Dates</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Days</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Conflicts</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {leaveRequests?.map((request) => (
                  <TableRow key={request.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {request.employee.display_name}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {request.employee.username}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2">
                        {leaveService.formatDateRange(request.start_date, request.end_date)}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Requested {formatDate(request.created)}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Chip
                        label={request.leave_type.name}
                        size="small"
                        style={{ backgroundColor: request.leave_type.color, color: 'white' }}
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2">
                        {request.days_requested} day{request.days_requested !== 1 ? 's' : ''}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      {getStatusChip(request.status)}
                    </TableCell>
                    
                    <TableCell>
                      {request.has_shift_conflicts && (
                        <Tooltip title="Click to view conflicting shifts">
                          <Chip
                            label="Conflicts"
                            size="small"
                            color="warning"
                            variant="outlined"
                            onClick={() => handleShowConflicts(request)}
                            sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'warning.light', opacity: 0.8 } }}
                          />
                        </Tooltip>
                      )}
                    </TableCell>
                    
                    <TableCell align="right">
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Tooltip title="View Details">
                          <IconButton
                            size="small"
                            onClick={() => handleViewDetails(request)}
                          >
                            <ViewIcon />
                          </IconButton>
                        </Tooltip>
                        
                        {canApprove(request) && (
                          <>
                            <Tooltip title="Approve">
                              <IconButton
                                size="small"
                                color="success"
                                onClick={() => handleApprove(request.id)}
                                disabled={!request.can_be_approved}
                              >
                                <ApproveIcon />
                              </IconButton>
                            </Tooltip>
                            
                            <Tooltip title="Reject">
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => {
                                  setSelectedLeaveRequest(request);
                                  setRejectDialogOpen(true);
                                }}
                              >
                                <RejectIcon />
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                        
                        {canCancel(request) && (
                          <Tooltip title="Cancel">
                            <IconButton
                              size="small"
                              color="warning"
                              onClick={() => handleCancel(request.id)}
                            >
                              <CancelIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          )}
          
          {/* Pagination */}
          {totalPages > 1 && (
            <Box display="flex" justifyContent="center" mt={2}>
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={(_, page) => setCurrentPage(page)}
                color="primary"
              />
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Floating Action Button for mobile */}
      <Fab
        color="primary"
        aria-label="add"
        sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          display: { xs: 'flex', sm: 'none' },
        }}
        onClick={() => setCreateDialogOpen(true)}
      >
        <AddIcon />
      </Fab>

      {/* Create Leave Request Dialog */}
      <Dialog open={createDialogOpen} onClose={handleCreateDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>Request Leave</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            {createError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {createError}
              </Alert>
            )}
            
            <Grid container spacing={2}>
              {/* Leave Type */}
              <Grid item xs={12}>
                <FormControl fullWidth required error={!createForm.leave_type_id}>
                  <InputLabel>Leave Type</InputLabel>
                  <Select
                    value={createForm.leave_type_id}
                    label="Leave Type"
                    onChange={(e) => handleCreateFormChange('leave_type_id', e.target.value)}
                  >
                    {(Array.isArray(leaveTypes) ? leaveTypes : []).map((type) => (
                      <MenuItem key={type.id} value={type.id.toString()}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box
                            sx={{
                              width: 12,
                              height: 12,
                              borderRadius: '50%',
                              backgroundColor: type.color,
                            }}
                          />
                          {type.name}
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                  {!createForm.leave_type_id && (
                    <FormHelperText>Please select a leave type</FormHelperText>
                  )}
                </FormControl>
              </Grid>

              {/* Start Date */}
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  required
                  label="Start Date"
                  type="date"
                  value={createForm.start_date}
                  onChange={(e) => handleCreateFormChange('start_date', e.target.value)}
                  InputLabelProps={{
                    shrink: true,
                  }}
                  inputProps={{
                    min: new Date().toISOString().split('T')[0], // Prevent past dates
                  }}
                  error={!createForm.start_date}
                  helperText={!createForm.start_date ? 'Please select a start date' : ''}
                />
              </Grid>

              {/* End Date */}
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  required
                  label="End Date"
                  type="date"
                  value={createForm.end_date}
                  onChange={(e) => handleCreateFormChange('end_date', e.target.value)}
                  InputLabelProps={{
                    shrink: true,
                  }}
                  inputProps={{
                    min: createForm.start_date || new Date().toISOString().split('T')[0],
                  }}
                  error={!createForm.end_date}
                  helperText={!createForm.end_date ? 'Please select an end date' : ''}
                />
              </Grid>

              {/* Days Requested */}
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Days Requested"
                  type="number"
                  value={createForm.days_requested}
                  onChange={(e) => handleCreateFormChange('days_requested', parseInt(e.target.value) || 1)}
                  inputProps={{
                    min: 1,
                    max: 365,
                  }}
                  helperText="Auto-calculated from dates, but you can adjust if needed"
                />
              </Grid>

              {/* Spacer */}
              <Grid item xs={12} sm={6} />

              {/* Reason */}
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label="Reason (Optional)"
                  placeholder="Explain the reason for your leave request..."
                  value={createForm.reason}
                  onChange={(e) => handleCreateFormChange('reason', e.target.value)}
                  helperText="Providing a reason helps with approval"
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCreateDialogClose} disabled={createLoading}>
            Cancel
          </Button>
          <Button 
            onClick={handleCreateSubmit} 
            variant="contained"
            disabled={createLoading || !createForm.leave_type_id || !createForm.start_date || !createForm.end_date}
            startIcon={createLoading ? <CircularProgress size={16} /> : undefined}
          >
            {createLoading ? 'Creating...' : 'Create Request'}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Simple Detail Dialog - placeholder for now */}
      <Dialog open={detailDialogOpen} onClose={() => setDetailDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Leave Request Details</DialogTitle>
        <DialogContent>
          {selectedLeaveRequest && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="h6">{selectedLeaveRequest.employee.display_name}</Typography>
              <Typography>
                {leaveService.formatDateRange(selectedLeaveRequest.start_date, selectedLeaveRequest.end_date)}
              </Typography>
              <Typography>Type: {selectedLeaveRequest.leave_type.name}</Typography>
              <Typography>Days: {selectedLeaveRequest.days_requested}</Typography>
              <Typography>Status: {selectedLeaveRequest.status_display}</Typography>
              {selectedLeaveRequest.reason && (
                <Typography>Reason: {selectedLeaveRequest.reason}</Typography>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
      
      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onClose={() => setRejectDialogOpen(false)}>
        <DialogTitle>Reject Leave Request</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Rejection Reason"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            placeholder="Please provide a reason for rejecting this leave request..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleReject} color="error" variant="contained">
            Reject
          </Button>
        </DialogActions>
      </Dialog>

      {/* Conflicts Dialog */}
      <Dialog
        open={conflictsDialogOpen}
        onClose={() => setConflictsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WarningIcon color="warning" />
            Shift Conflicts
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedLeaveRequest && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                The following shifts conflict with the leave request from{' '}
                {formatDate(selectedLeaveRequest.start_date)} to{' '}
                {formatDate(selectedLeaveRequest.end_date)}:
              </Typography>
            </Box>
          )}
          
          {loadingConflicts ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Shift Name</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Start Date & Time</TableCell>
                    <TableCell>End Date & Time</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {conflictingShifts.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography variant="body2" color="text.secondary">
                          No conflicting shifts found.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    conflictingShifts.map((shift) => (
                      <TableRow key={shift.id}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {shift.shift_name}
                          </Typography>
                          {shift.notes && (
                            <Typography variant="caption" color="text.secondary" display="block">
                              {shift.notes}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={shift.shift_type}
                            size="small"
                            variant="outlined"
                            color="primary"
                          />
                        </TableCell>
                        <TableCell>
                          {formatDateTime(shift.start_datetime)}
                        </TableCell>
                        <TableCell>
                          {formatDateTime(shift.end_datetime)}
                        </TableCell>
                        <TableCell>
                          {shift.duration_hours} hours
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={shift.status}
                            size="small"
                            color={shift.status === 'confirmed' ? 'success' : 'default'}
                          />
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
          
          {conflictingShifts.length > 0 && (
            <Alert severity="info" sx={{ mt: 2 }}>
              <AlertTitle>What to do about conflicts?</AlertTitle>
              You may need to find shift swaps or request coverage for these conflicting shifts before your leave can be approved.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConflictsDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LeaveRequestPage;
