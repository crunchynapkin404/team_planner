import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Chip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Paper,
  Badge,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
} from '@mui/material';
import {
  SwapHoriz,
  Add,
  CheckCircle,
  Cancel,
  MoreVert,
  Refresh,
  Visibility,
} from '@mui/icons-material';
import { userService, type TeamMember, type UserShift, type SwapRequest } from '../services/userService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`swaps-tabpanel-${index}`}
      aria-labelledby={`swaps-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const ShiftSwapsPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [incomingSwaps, setIncomingSwaps] = useState<SwapRequest[]>([]);
  const [outgoingSwaps, setOutgoingSwaps] = useState<SwapRequest[]>([]);
  const [allSwaps, setAllSwaps] = useState<SwapRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSwap, setSelectedSwap] = useState<SwapRequest | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [responseOpen, setResponseOpen] = useState(false);
  const [responseAction, setResponseAction] = useState<'approve' | 'reject'>('approve');
  const [responseNotes, setResponseNotes] = useState('');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [menuSwapId, setMenuSwapId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  
  // Create swap request state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [userShifts, setUserShifts] = useState<UserShift[]>([]);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [employeeShifts, setEmployeeShifts] = useState<UserShift[]>([]);
  const [createForm, setCreateForm] = useState({
    requesting_shift_id: '',
    target_employee_id: '',
    target_shift_id: '',
    reason: '',
  });
  const [createLoading, setCreateLoading] = useState(false);

  // Helper function to get display name from user object
  const getDisplayName = (user: { username: string; first_name?: string; last_name?: string }) => {
    const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
    return fullName || user.username;
  };

  useEffect(() => {
    fetchSwapRequests();
  }, []);

  const fetchSwapRequests = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get incoming and outgoing swap requests using the userService
      const [incomingData, outgoingData] = await Promise.all([
        userService.getIncomingSwapRequests(),
        userService.getOutgoingSwapRequests(),
      ]);
      
      setIncomingSwaps(incomingData);
      setOutgoingSwaps(outgoingData);
      
      // Combine all swaps for the "All" tab
      const combined = [...incomingData, ...outgoingData];
      // Remove duplicates based on ID
      const uniqueSwaps = combined.filter((swap, index, self) => 
        index === self.findIndex(s => s.id === swap.id)
      );
      setAllSwaps(uniqueSwaps);
    } catch (err) {
      setError('Failed to fetch swap requests');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleDetailsOpen = (swap: SwapRequest) => {
    setSelectedSwap(swap);
    setDetailsOpen(true);
  };

  const handleResponseOpen = (swap: SwapRequest, action: 'approve' | 'reject') => {
    setSelectedSwap(swap);
    setResponseAction(action);
    setResponseNotes('');
    setResponseOpen(true);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, swapId: number) => {
    setAnchorEl(event.currentTarget);
    setMenuSwapId(swapId);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setMenuSwapId(null);
  };

  const handleStatusFilterChange = (event: SelectChangeEvent) => {
    setStatusFilter(event.target.value);
  };

  const handleCreateDialogOpen = async () => {
    setCreateDialogOpen(true);
    
    // Fetch user shifts and team members
    try {
      const [shiftsData, membersData] = await Promise.all([
        userService.getUserShifts(),
        userService.getTeamMembers(),
      ]);
      setUserShifts(shiftsData);
      setTeamMembers(membersData);
    } catch (err) {
      setError('Failed to load data for creating swap request');
      console.error('Load error:', err);
    }
  };

  const handleCreateDialogClose = () => {
    setCreateDialogOpen(false);
    setCreateForm({
      requesting_shift_id: '',
      target_employee_id: '',
      target_shift_id: '',
      reason: '',
    });
    setEmployeeShifts([]);
  };

  const handleCreateFormChange = async (field: string, value: string) => {
    setCreateForm(prev => ({ ...prev, [field]: value }));
    
    // If target employee changed, fetch their shifts
    if (field === 'target_employee_id' && value) {
      try {
        const shifts = await userService.getEmployeeShifts(parseInt(value));
        setEmployeeShifts(shifts);
      } catch (err) {
        console.error('Failed to fetch employee shifts:', err);
        setEmployeeShifts([]);
      }
    }
  };

  const handleCreateSubmit = async () => {
    if (!createForm.requesting_shift_id || !createForm.target_employee_id) {
      setError('Please select both a shift to give up and a target employee');
      return;
    }

    setCreateLoading(true);
    try {
      await userService.createSwapRequest({
        requesting_shift_id: parseInt(createForm.requesting_shift_id),
        target_employee_id: parseInt(createForm.target_employee_id),
        target_shift_id: createForm.target_shift_id ? parseInt(createForm.target_shift_id) : undefined,
        reason: createForm.reason,
      });
      
      handleCreateDialogClose();
      await fetchSwapRequests(); // Refresh the data
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.error || 'Failed to create swap request');
      console.error('Create error:', err);
    } finally {
      setCreateLoading(false);
    }
  };

  const submitResponse = async () => {
    if (!selectedSwap) return;

    try {
      await userService.respondToSwapRequest(selectedSwap.id, responseAction, responseNotes);
      setResponseOpen(false);
      setSelectedSwap(null);
      setResponseNotes('');
      await fetchSwapRequests(); // Refresh the data
    } catch (err) {
      setError('Failed to respond to swap request');
      console.error('Response error:', err);
    }
  };

  const formatDateTime = (dateTimeString: string) => {
    const date = new Date(dateTimeString);
    return date.toLocaleString();
  };

  const formatShiftTime = (shift: SwapRequest['requesting_shift']) => {
    const start = new Date(shift.start_time);
    const end = new Date(shift.end_time);
    return `${start.toLocaleDateString()} ${start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - ${end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  };

  const getStatusColor = (status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (status) {
      case 'pending': return 'warning';
      case 'approved': return 'success';
      case 'rejected': return 'error';
      case 'cancelled': return 'secondary';
      default: return 'default';
    }
  };

  const filterSwapsByStatus = (swaps: SwapRequest[]) => {
    if (statusFilter === 'all') return swaps;
    return swaps.filter(swap => swap.status === statusFilter);
  };

  const renderSwapCard = (swap: SwapRequest, showRequester: boolean = true) => (
    <Card key={swap.id} sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SwapHoriz color="primary" />
            <Typography variant="h6">
              {showRequester 
                ? `${getDisplayName(swap.requester)} wants to swap`
                : `Swap with ${getDisplayName(swap.target_employee)}`
              }
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              label={swap.status}
              color={getStatusColor(swap.status)}
              size="small"
            />
            <IconButton
              size="small"
              onClick={(e) => handleMenuOpen(e, swap.id)}
            >
              <MoreVert />
            </IconButton>
          </Box>
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              {showRequester ? 'Their Shift:' : 'Your Shift:'}
            </Typography>
            <Card variant="outlined" sx={{ p: 1 }}>
              <Typography variant="body2">
                <strong>{swap.requesting_shift.title}</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {formatShiftTime(swap.requesting_shift)}
              </Typography>
              <Chip
                label={swap.requesting_shift.shift_type}
                size="small"
                variant="outlined"
                sx={{ mt: 0.5 }}
              />
            </Card>
          </Grid>

          {swap.target_shift && (
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                {showRequester ? 'Your Shift:' : 'Their Shift:'}
              </Typography>
              <Card variant="outlined" sx={{ p: 1 }}>
                <Typography variant="body2">
                  <strong>{swap.target_shift.title}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {formatShiftTime(swap.target_shift)}
                </Typography>
                <Chip
                  label={swap.target_shift.shift_type}
                  size="small"
                  variant="outlined"
                  sx={{ mt: 0.5 }}
                />
              </Card>
            </Grid>
          )}
        </Grid>

        {swap.reason && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Reason:
            </Typography>
            <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
              "{swap.reason}"
            </Typography>
          </Box>
        )}

        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Created: {formatDateTime(swap.created_at)}
          </Typography>

          {swap.status === 'pending' && showRequester && (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                size="small"
                variant="contained"
                color="success"
                startIcon={<CheckCircle />}
                onClick={() => handleResponseOpen(swap, 'approve')}
              >
                Approve
              </Button>
              <Button
                size="small"
                variant="outlined"
                color="error"
                startIcon={<Cancel />}
                onClick={() => handleResponseOpen(swap, 'reject')}
              >
                Reject
              </Button>
            </Box>
          )}
        </Box>

        {swap.response_notes && (
          <Box sx={{ mt: 1, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Response: {swap.response_notes}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', minHeight: '100%' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Shift Swaps
        </Typography>
        <Stack direction="row" spacing={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={handleStatusFilterChange}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="approved">Approved</MenuItem>
              <MenuItem value="rejected">Rejected</MenuItem>
              <MenuItem value="cancelled">Cancelled</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchSwapRequests}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={handleCreateDialogOpen}
          >
            New Swap Request
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="swap request tabs">
          <Tab 
            label={
              <Badge badgeContent={filterSwapsByStatus(incomingSwaps.filter(s => s.status === 'pending')).length} color="warning">
                Incoming
              </Badge>
            } 
          />
          <Tab label="Outgoing" />
          <Tab label="All" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      <TabPanel value={tabValue} index={0}>
        <Typography variant="h6" gutterBottom>
          Incoming Swap Requests
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Requests from other engineers who want to swap shifts with you.
        </Typography>
        {filterSwapsByStatus(incomingSwaps).length === 0 ? (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No incoming swap requests
            </Typography>
          </Paper>
        ) : (
          filterSwapsByStatus(incomingSwaps).map(swap => renderSwapCard(swap, true))
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Typography variant="h6" gutterBottom>
          Outgoing Swap Requests
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Requests you've sent to other engineers.
        </Typography>
        {filterSwapsByStatus(outgoingSwaps).length === 0 ? (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No outgoing swap requests
            </Typography>
          </Paper>
        ) : (
          filterSwapsByStatus(outgoingSwaps).map(swap => renderSwapCard(swap, false))
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Typography variant="h6" gutterBottom>
          All Swap Requests
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          All your swap requests (incoming and outgoing).
        </Typography>
        {filterSwapsByStatus(allSwaps).length === 0 ? (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No swap requests
            </Typography>
          </Paper>
        ) : (
          filterSwapsByStatus(allSwaps).map(swap => renderSwapCard(swap, true))
        )}
      </TabPanel>

      {/* Action Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => { 
          const swap = allSwaps.find(s => s.id === menuSwapId);
          if (swap) handleDetailsOpen(swap);
          handleMenuClose();
        }}>
          <Visibility sx={{ mr: 1 }} /> View Details
        </MenuItem>
      </Menu>

      {/* Details Dialog */}
      <Dialog open={detailsOpen} onClose={() => setDetailsOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Swap Request Details
        </DialogTitle>
        <DialogContent>
          {selectedSwap && (
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="h6" gutterBottom>
                    Requester
                  </Typography>
                  <Typography>{getDisplayName(selectedSwap.requester)}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    @{selectedSwap.requester.username}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="h6" gutterBottom>
                    Target
                  </Typography>
                  <Typography>{getDisplayName(selectedSwap.target_employee)}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    @{selectedSwap.target_employee.username}
                  </Typography>
                </Grid>
              </Grid>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>
                Shift Details
              </Typography>
              {/* Add more detailed shift information here */}
              
              {selectedSwap.reason && (
                <>
                  <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                    Reason
                  </Typography>
                  <Typography>{selectedSwap.reason}</Typography>
                </>
              )}

              {selectedSwap.response_notes && (
                <>
                  <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                    Response Notes
                  </Typography>
                  <Typography>{selectedSwap.response_notes}</Typography>
                </>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Response Dialog */}
      <Dialog open={responseOpen} onClose={() => setResponseOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {responseAction === 'approve' ? 'Approve' : 'Reject'} Swap Request
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Are you sure you want to {responseAction} this swap request?
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            label="Response Notes (Optional)"
            value={responseNotes}
            onChange={(e) => setResponseNotes(e.target.value)}
            sx={{ mt: 2 }}
            placeholder={`Add a note about your ${responseAction} decision...`}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResponseOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            color={responseAction === 'approve' ? 'success' : 'error'}
            onClick={submitResponse}
          >
            {responseAction === 'approve' ? 'Approve' : 'Reject'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create Swap Request Dialog */}
      <Dialog open={createDialogOpen} onClose={handleCreateDialogClose} maxWidth="md" fullWidth>
        <DialogTitle>
          Create New Swap Request
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={3}>
              {/* Your Shift Selection */}
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Your Shift to Give Up</InputLabel>
                  <Select
                    value={createForm.requesting_shift_id}
                    label="Your Shift to Give Up"
                    onChange={(e) => handleCreateFormChange('requesting_shift_id', e.target.value)}
                  >
                    {userShifts.map((shift) => (
                      <MenuItem key={shift.id} value={shift.id.toString()}>
                        <Box>
                          <Typography variant="body2">
                            <strong>{shift.title}</strong>
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(shift.start_time).toLocaleString()} - {new Date(shift.end_time).toLocaleTimeString()}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Target Employee Selection */}
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Target Employee</InputLabel>
                  <Select
                    value={createForm.target_employee_id}
                    label="Target Employee"
                    onChange={(e) => handleCreateFormChange('target_employee_id', e.target.value)}
                  >
                    {teamMembers.map((member) => (
                      <MenuItem key={member.id} value={member.id.toString()}>
                        {member.display_name} (@{member.username})
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Target Shift Selection (Optional) */}
              {createForm.target_employee_id && (
                <Grid item xs={12}>
                  <FormControl fullWidth>
                    <InputLabel>Target Shift (Optional)</InputLabel>
                    <Select
                      value={createForm.target_shift_id}
                      label="Target Shift (Optional)"
                      onChange={(e) => handleCreateFormChange('target_shift_id', e.target.value)}
                    >
                      <MenuItem value="">
                        <em>None - Employee will just take over your shift</em>
                      </MenuItem>
                      {employeeShifts.map((shift) => (
                        <MenuItem key={shift.id} value={shift.id.toString()}>
                          <Box>
                            <Typography variant="body2">
                              <strong>{shift.title}</strong>
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {new Date(shift.start_time).toLocaleString()} - {new Date(shift.end_time).toLocaleTimeString()}
                            </Typography>
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              )}

              {/* Reason */}
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Reason for Swap Request"
                  value={createForm.reason}
                  onChange={(e) => handleCreateFormChange('reason', e.target.value)}
                  placeholder="Explain why you need this swap..."
                  helperText="Providing a clear reason increases the chances of approval"
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
            variant="contained" 
            onClick={handleCreateSubmit}
            disabled={createLoading || !createForm.requesting_shift_id || !createForm.target_employee_id}
            startIcon={createLoading ? <CircularProgress size={20} /> : <Add />}
          >
            {createLoading ? 'Creating...' : 'Create Swap Request'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ShiftSwapsPage;
