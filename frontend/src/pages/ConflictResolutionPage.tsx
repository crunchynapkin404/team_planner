import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Divider,
  Paper,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Info as InfoIcon,
  Psychology as AIIcon,
} from '@mui/icons-material';
import { format, parseISO, startOfMonth, endOfMonth, addMonths } from 'date-fns';
import leaveConflictService, {
  type ConflictDashboard,
  type Recommendation,
} from '../services/leaveConflictService';
import { apiClient } from '../services/apiClient';

interface LeaveRequest {
  id: number;
  employee: number;
  employee_name: string;
  start_date: string;
  end_date: string;
  days_requested: number;
  leave_type: string;
  status: string;
  created: string;
}

const ConflictResolutionPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [conflicts, setConflicts] = useState<ConflictDashboard | null>(null);
  const [startDate, setStartDate] = useState(format(startOfMonth(new Date()), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(endOfMonth(addMonths(new Date(), 1)), 'yyyy-MM-dd'));
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [dateRequests, setDateRequests] = useState<LeaveRequest[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [resolveDialogOpen, setResolveDialogOpen] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    loadConflicts();
  }, [startDate, endDate]);

  const loadConflicts = async () => {
    setLoading(true);
    try {
      const data = await leaveConflictService.getConflicts({
        start_date: startDate,
        end_date: endDate,
      });
      setConflicts(data);
    } catch (error) {
      console.error('Failed to load conflicts:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadRequestsForDate = async (date: string) => {
    try {
      const response = await apiClient.get<{ results: LeaveRequest[] }>(
        `/api/leaves/requests/?start_date=${date}&end_date=${date}&status=pending`
      );
      setDateRequests(response.results || []);
      
      // Get AI recommendation if multiple requests
      if (response.results && response.results.length > 1) {
        const requestIds = response.results.map(r => r.id);
        const rec = await leaveConflictService.getRecommendation(requestIds);
        setRecommendation(rec);
      } else {
        setRecommendation(null);
      }
    } catch (error) {
      console.error('Failed to load requests:', error);
      setDateRequests([]);
      setRecommendation(null);
    }
  };

  const handleDateClick = async (date: string) => {
    setSelectedDate(date);
    setResolveDialogOpen(true);
    await loadRequestsForDate(date);
  };

  const handleResolve = async (approveId: number) => {
    const rejectIds = dateRequests.filter(r => r.id !== approveId).map(r => r.id);
    
    setResolving(true);
    try {
      await leaveConflictService.resolveConflict({
        approve_request_id: approveId,
        reject_request_ids: rejectIds,
        resolution_notes: resolutionNotes,
      });
      
      setResolveDialogOpen(false);
      setResolutionNotes('');
      await loadConflicts();
    } catch (error) {
      console.error('Failed to resolve conflict:', error);
    } finally {
      setResolving(false);
    }
  };

  const handleClose = () => {
    setResolveDialogOpen(false);
    setSelectedDate(null);
    setDateRequests([]);
    setRecommendation(null);
    setResolutionNotes('');
  };

  if (loading && !conflicts) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Leave Conflict Resolution</Typography>
        <Button
          startIcon={<RefreshIcon />}
          onClick={loadConflicts}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {/* Date Range Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4}>
              <TextField
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Typography variant="body2" color="text.secondary">
                Team Size: {conflicts?.total_team_size || 0} members
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <WarningIcon color="error" />
                <Typography variant="h6">Conflicts</Typography>
              </Box>
              <Typography variant="h3">{conflicts?.conflict_days.length || 0}</Typography>
              <Typography variant="body2" color="text.secondary">
                Days with multiple leave requests
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <WarningIcon color="warning" />
                <Typography variant="h6">Understaffed</Typography>
              </Box>
              <Typography variant="h3">{conflicts?.understaffed_days.length || 0}</Typography>
              <Typography variant="body2" color="text.secondary">
                Days below minimum staffing
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <InfoIcon color="info" />
                <Typography variant="h6">Warnings</Typography>
              </Box>
              <Typography variant="h3">{conflicts?.warning_days.length || 0}</Typography>
              <Typography variant="body2" color="text.secondary">
                Days close to minimum staffing
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Conflict Days List */}
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Conflict Days Requiring Resolution
          </Typography>

          {!conflicts || conflicts.conflict_days.length === 0 ? (
            <Alert severity="success" icon={<CheckIcon />}>
              No conflicts found for the selected date range. All leave requests can proceed
              smoothly!
            </Alert>
          ) : (
            <List>
              {conflicts.conflict_days.map((day, index) => (
                <React.Fragment key={day.date}>
                  {index > 0 && <Divider />}
                  <ListItem
                    button
                    onClick={() => handleDateClick(day.date)}
                    sx={{
                      '&:hover': {
                        backgroundColor: 'action.hover',
                      },
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {format(parseISO(day.date), 'EEEE, MMM d, yyyy')}
                          </Typography>
                          <Chip
                            size="small"
                            label={`${day.leave_count} requests`}
                            color="error"
                          />
                        </Box>
                      }
                      secondary={`${day.employees_on_leave.length} employees requesting leave`}
                    />
                    <Button variant="outlined" size="small">
                      Resolve
                    </Button>
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Understaffed Days */}
      {conflicts && conflicts.understaffed_days.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Understaffed Days
            </Typography>
            <List dense>
              {conflicts.understaffed_days.map((day, index) => (
                <React.Fragment key={day.date}>
                  {index > 0 && <Divider />}
                  <ListItem>
                    <ListItemText
                      primary={format(parseISO(day.date), 'MMM d, yyyy')}
                      secondary={`${day.available_staff} available / ${day.required_staff} required (${day.shortage} short)`}
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Resolution Dialog */}
      <Dialog open={resolveDialogOpen} onClose={handleClose} maxWidth="md" fullWidth>
        <DialogTitle>
          Resolve Conflict for {selectedDate && format(parseISO(selectedDate), 'MMM d, yyyy')}
        </DialogTitle>
        <DialogContent dividers>
          {dateRequests.length === 0 ? (
            <Box sx={{ py: 4, textAlign: 'center' }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box>
              {/* AI Recommendation */}
              {recommendation && (
                <Alert
                  severity="info"
                  icon={<AIIcon />}
                  sx={{ mb: 3 }}
                >
                  <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                    AI Recommendation:
                  </Typography>
                  <Typography variant="body2">
                    Approve request from <strong>{recommendation.recommended_request.employee}</strong> based on:
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    {recommendation.recommendation_details.seniority && (
                      <Typography variant="caption" display="block">
                        • Seniority: {recommendation.recommendation_details.seniority.reason}
                      </Typography>
                    )}
                    {recommendation.recommendation_details.first_request && (
                      <Typography variant="caption" display="block">
                        • First Request: {recommendation.recommendation_details.first_request.reason}
                      </Typography>
                    )}
                    {recommendation.recommendation_details.leave_balance && (
                      <Typography variant="caption" display="block">
                        • Leave Balance: {recommendation.recommendation_details.leave_balance.reason}
                      </Typography>
                    )}
                  </Box>
                </Alert>
              )}

              {/* Leave Requests */}
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Conflicting Leave Requests:
              </Typography>
              <List>
                {dateRequests.map((request) => (
                  <Paper key={request.id} sx={{ mb: 2, p: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Box>
                        <Typography variant="subtitle2" fontWeight="bold">
                          {request.employee_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {format(parseISO(request.start_date), 'MMM d')} -{' '}
                          {format(parseISO(request.end_date), 'MMM d, yyyy')} ({request.days_requested} days)
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Type: {request.leave_type}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Requested: {format(parseISO(request.created), 'MMM d, yyyy h:mm a')}
                        </Typography>
                        {recommendation && recommendation.recommended_request.id === request.id && (
                          <Chip
                            size="small"
                            label="Recommended"
                            color="primary"
                            sx={{ mt: 1 }}
                          />
                        )}
                      </Box>
                      <Button
                        variant="contained"
                        color="primary"
                        size="small"
                        onClick={() => handleResolve(request.id)}
                        disabled={resolving}
                      >
                        Approve This
                      </Button>
                    </Box>
                  </Paper>
                ))}
              </List>

              {/* Resolution Notes */}
              <TextField
                label="Resolution Notes (optional)"
                multiline
                rows={3}
                fullWidth
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                placeholder="Add notes explaining your decision..."
                sx={{ mt: 2 }}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={resolving}>
            Cancel
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ConflictResolutionPage;
