/**
 * Schedule Orchestrator Form - Simplified interface for shift generation
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  FormControlLabel,
  Checkbox,
  Switch,
  Alert,
  CircularProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { 
  PlayArrow, 
  Schedule, 
  AutoMode,
  CheckCircle,
  Cancel,
} from '@mui/icons-material';
import { apiClient } from '../../../services/apiClient';

const ScheduleOrchestratorForm: React.FC = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Auto-scheduling state
  const [autoSchedulingEnabled, setAutoSchedulingEnabled] = useState(false);
  const [shiftTypeToggles, setShiftTypeToggles] = useState({
    incidents: false,
    waakdienst: false,
    incidents_standby: false,
  });
  
  // Teams and options
  const [teams, setTeams] = useState<{id: number, name: string}[]>([]);
  const [dryRun, setDryRun] = useState(true);
  const [selectedTeam, setSelectedTeam] = useState<number>(1);
  const [selectedShiftTypes, setSelectedShiftTypes] = useState<string[]>(['incidents', 'waakdienst']);

  // Load current auto-scheduling status
  useEffect(() => {
    loadAutoSchedulingStatus();
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      // Check if user is authenticated
      if (!apiClient.isAuthenticated()) {
        console.warn('User not authenticated, using fallback teams');
        throw new Error('Not authenticated');
      }

      console.log('Making teams API request with token:', apiClient.getToken()?.substring(0, 10) + '...');
      const response = await apiClient.get('/api/teams/') as any;
      console.log('Teams API response type:', typeof response);
      console.log('Teams API response:', response);
      
      // The teams API should return a direct array of team objects
      if (!Array.isArray(response)) {
        console.error('Expected array but got:', typeof response, response);
        // Try to extract data if it's wrapped
        if (response && typeof response === 'object') {
          // Check for common wrapper patterns
          if (Array.isArray(response.data)) {
            console.log('Found teams in response.data');
            const teams = response.data;
            const validTeams = teams
              .filter((team: any) => team && typeof team === 'object' && team.id)
              .map((team: any) => ({
                id: Number(team.id),
                name: String(team.name || `Team ${team.id}`),
              }));
            setTeams(validTeams);
            if (validTeams.length > 0 && !validTeams.find((t: any) => t.id === selectedTeam)) {
              setSelectedTeam(validTeams[0].id);
            }
            return;
          }
          if (Array.isArray(response.results)) {
            console.log('Found teams in response.results');
            const teams = response.results;
            const validTeams = teams
              .filter((team: any) => team && typeof team === 'object' && team.id)
              .map((team: any) => ({
                id: Number(team.id),
                name: String(team.name || `Team ${team.id}`),
              }));
            setTeams(validTeams);
            if (validTeams.length > 0 && !validTeams.find((t: any) => t.id === selectedTeam)) {
              setSelectedTeam(validTeams[0].id);
            }
            return;
          }
        }
        throw new Error(`Expected array but got ${typeof response}`);
      }
      
      // Map teams to our expected format
      const validTeams = response
        .filter((team: any) => team && typeof team === 'object' && team.id)
        .map((team: any) => ({
          id: Number(team.id),
          name: String(team.name || `Team ${team.id}`),
        }));
      
      console.log('Processed teams:', validTeams);
      
      if (validTeams.length === 0) {
        throw new Error('No valid teams found');
      }
      
      setTeams(validTeams);
      
      // Set default team to first available team if current selection doesn't exist
      const teamExists = validTeams.find((t: any) => t.id === selectedTeam);
      if (!teamExists) {
        setSelectedTeam(validTeams[0].id);
      }
    } catch (error: any) {
      console.error('Failed to load teams:', error);
      
      // Show authentication error specifically
      if (error.status === 401 || error.message?.includes('Authentication') || error.message?.includes('authenticated')) {
        setValidationError('Please log in to access team data');
      }
      
      // Fallback to hardcoded teams
      const fallbackTeams = [
        { id: 1, name: 'Team Alpha' },
        { id: 2, name: 'Team Beta' },
        { id: 3, name: 'Team Gamma' }
      ];
      console.log('Using fallback teams:', fallbackTeams);
      setTeams(fallbackTeams);
      setSelectedTeam(1);
    }
  };

  const loadAutoSchedulingStatus = async () => {
    try {
      const response = await apiClient.get('/orchestrators/api/auto-overview/') as any;
      
      // Check if global auto-scheduling is enabled
      setAutoSchedulingEnabled(response.enabled || false);
      
      // Update shift type toggles based on team status
      if (response.teams && selectedTeam) {
        const teamData = response.teams.find((t: any) => t.team_id === selectedTeam);
        if (teamData) {
          setShiftTypeToggles({
            incidents: teamData.shift_types?.incidents?.enabled || false,
            waakdienst: teamData.shift_types?.waakdienst?.enabled || false,
            incidents_standby: teamData.shift_types?.incidents_standby?.enabled || false,
          });
        }
      }
    } catch (error) {
      console.error('Failed to load auto-scheduling status:', error);
    }
  };

  const handleGenerate6Months = async () => {
    setIsSubmitting(true);
    setValidationError(null);
    setSuccessMessage(null);

    // Calculate start and end dates for 6 months
    const startDate = new Date();
    const endDate = new Date();
    endDate.setMonth(endDate.getMonth() + 6);

    const requestData = {
      name: `6-Month Initial Schedule - ${startDate.toISOString().split('T')[0]}`,
      description: 'Initial 6-month schedule generation',
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0],
      preview_only: dryRun,
      team_id: selectedTeam,
      schedule_incidents: selectedShiftTypes.includes('incidents'),
      schedule_incidents_standby: selectedShiftTypes.includes('incidents_standby'),
      schedule_waakdienst: selectedShiftTypes.includes('waakdienst'),
    };

    console.log('Sending orchestrator create request:', requestData);

    try {
      const response = await apiClient.post('/orchestrators/api/create/', requestData) as any;

      console.log('Orchestrator create API response:', response);

      if (dryRun) {
        setSuccessMessage(`Preview completed: ${response.total_shifts || 0} assignments planned`);
      } else {
        setSuccessMessage(`6-month schedule generated successfully: ${response.total_shifts || 0} shifts created`);
      }
      
      // Show breakdown if available
      if (response.incidents_shifts || response.waakdienst_shifts || response.incidents_standby_shifts) {
        const breakdown: string[] = [];
        if (response.incidents_shifts) breakdown.push(`${response.incidents_shifts} incidents`);
        if (response.waakdienst_shifts) breakdown.push(`${response.waakdienst_shifts} waakdienst`);
        if (response.incidents_standby_shifts) breakdown.push(`${response.incidents_standby_shifts} standby`);
        
        if (breakdown.length > 0) {
          setSuccessMessage(prev => `${prev} (${breakdown.join(', ')})`);
        }
      }
      
      // Show additional details if available
      if (response.details) {
        console.log('Generation details:', response.details);
      }
      if (response.errors && response.errors.length > 0) {
        console.warn('Generation warnings/errors:', response.errors);
      }
    } catch (error: any) {
      console.error('Orchestrator create API error:', error);
      setValidationError(error?.response?.data?.error || error.message || 'Failed to generate schedule');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEnableAutoScheduling = async () => {
    setIsSubmitting(true);
    setValidationError(null);

    try {
      await apiClient.post('/orchestrators/api/enable-auto/');
      setAutoSchedulingEnabled(true);
      setSuccessMessage('Automatic scheduling enabled - will run nightly at 2:00 AM');
      await loadAutoSchedulingStatus();
    } catch (error: any) {
      setValidationError(error?.response?.data?.error || error.message || 'Failed to enable auto-scheduling');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleShiftType = async (shiftType: string, enabled: boolean) => {
    if (!selectedTeam) return;

    setIsSubmitting(true);
    setValidationError(null);

    try {
      await apiClient.post('/orchestrators/api/auto-toggle/', {
        team_id: selectedTeam,
        shift_type: shiftType,
        enabled: enabled,
      });

      setShiftTypeToggles(prev => ({
        ...prev,
        [shiftType]: enabled,
      }));

      setSuccessMessage(`${shiftType} auto-scheduling ${enabled ? 'enabled' : 'disabled'}`);
    } catch (error: any) {
      setValidationError(error?.response?.data?.error || error.message || 'Failed to toggle shift type');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleShiftTypeChange = (shiftType: string, checked: boolean) => {
    if (checked) {
      setSelectedShiftTypes(prev => [...prev, shiftType]);
    } else {
      setSelectedShiftTypes(prev => prev.filter(type => type !== shiftType));
    }
  };

  const isLoading = isSubmitting;

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Schedule color="primary" />
        Shift Orchestrator
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Generate the initial 6-month schedule and enable automatic weekly rolling
      </Typography>

      {validationError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {validationError}
        </Alert>
      )}

      {successMessage && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {successMessage}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Team and Shift Type Selection */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Configuration
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Team</InputLabel>
                    <Select
                      value={teams.length > 0 ? selectedTeam : ''}
                      label="Team"
                      onChange={(e) => setSelectedTeam(e.target.value as number)}
                      disabled={isLoading}
                    >
                      {teams && teams.length > 0 ? teams.map((team) => (
                        <MenuItem key={team.id} value={team.id}>
                          {team.name}
                        </MenuItem>
                      )) : (
                        <MenuItem value="">Loading teams...</MenuItem>
                      )}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Shift Types to Generate:
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedShiftTypes.includes('incidents')}
                          onChange={(e) => handleShiftTypeChange('incidents', e.target.checked)}
                          disabled={isLoading}
                        />
                      }
                      label="Incidents (Mon-Fri 8:00-17:00)"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedShiftTypes.includes('waakdienst')}
                          onChange={(e) => handleShiftTypeChange('waakdienst', e.target.checked)}
                          disabled={isLoading}
                        />
                      }
                      label="Waakdienst (Wed-Wed on-call)"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedShiftTypes.includes('incidents_standby')}
                          onChange={(e) => handleShiftTypeChange('incidents_standby', e.target.checked)}
                          disabled={isLoading}
                        />
                      }
                      label="Incidents-Standby (backup)"
                    />
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Initial 6-Month Generation */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                1. Generate Initial 6-Month Schedule
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Create shifts for the next 6 months for the selected team and shift types.
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={dryRun}
                      onChange={(e) => setDryRun(e.target.checked)}
                      disabled={isLoading}
                    />
                  }
                  label="Preview Mode (dry run - no actual shifts created)"
                />
              </Box>

              <Button
                variant="contained"
                size="large"
                startIcon={isLoading ? <CircularProgress size={20} /> : <PlayArrow />}
                onClick={handleGenerate6Months}
                disabled={isLoading || selectedShiftTypes.length === 0 || teams.length === 0}
                sx={{ minWidth: 250 }}
              >
                {isLoading ? 'Generating...' : dryRun ? 'Preview 6-Month Schedule' : 'Generate 6-Month Schedule'}
              </Button>
              
              {selectedShiftTypes.length === 0 && (
                <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                  Please select at least one shift type to generate
                </Typography>
              )}
              
              {teams.length === 0 && (
                <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                  No teams available. Please check your team configuration.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Automatic Rolling */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                2. Enable Automatic Weekly Rolling
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Once enabled, the system will automatically extend the schedule weekly to maintain 6 months ahead.
                Runs nightly at 2:00 AM.
              </Typography>

              {!autoSchedulingEnabled ? (
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={isLoading ? <CircularProgress size={20} /> : <AutoMode />}
                  onClick={handleEnableAutoScheduling}
                  disabled={isLoading}
                  sx={{ minWidth: 250, mb: 2 }}
                >
                  {isLoading ? 'Enabling...' : 'Enable Auto-Scheduling'}
                </Button>
              ) : (
                <Box>
                  <Alert severity="success" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                      ✅ Automatic scheduling is enabled - runs nightly at 2:00 AM
                    </Typography>
                  </Alert>
                  
                  <Typography variant="subtitle2" gutterBottom>
                    Shift Type Controls:
                  </Typography>
                  
                  <List dense>
                    <ListItem>
                      <ListItemText 
                        primary="Incidents (Mon-Fri 8:00-17:00)"
                        secondary="Business hours coverage"
                      />
                      <ListItemSecondaryAction>
                        <Switch
                          checked={shiftTypeToggles.incidents}
                          onChange={(e) => handleToggleShiftType('incidents', e.target.checked)}
                          disabled={isLoading}
                          color="primary"
                        />
                      </ListItemSecondaryAction>
                    </ListItem>
                    
                    <ListItem>
                      <ListItemText 
                        primary="Waakdienst (Wed 17:00 - Wed 8:00)"
                        secondary="On-call coverage"
                      />
                      <ListItemSecondaryAction>
                        <Switch
                          checked={shiftTypeToggles.waakdienst}
                          onChange={(e) => handleToggleShiftType('waakdienst', e.target.checked)}
                          disabled={isLoading}
                          color="primary"
                        />
                      </ListItemSecondaryAction>
                    </ListItem>
                    
                    <ListItem>
                      <ListItemText 
                        primary="Incidents-Standby (Mon-Fri 8:00-17:00)"
                        secondary="Backup coverage"
                      />
                      <ListItemSecondaryAction>
                        <Switch
                          checked={shiftTypeToggles.incidents_standby}
                          onChange={(e) => handleToggleShiftType('incidents_standby', e.target.checked)}
                          disabled={isLoading}
                          color="primary"
                        />
                      </ListItemSecondaryAction>
                    </ListItem>
                  </List>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Current Status */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Current Status
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip 
                  label={`Auto-Scheduling: ${autoSchedulingEnabled ? 'Enabled' : 'Disabled'}`}
                  color={autoSchedulingEnabled ? 'success' : 'default'}
                  icon={autoSchedulingEnabled ? <CheckCircle /> : <Cancel />}
                />
                <Chip 
                  label={`Incidents: ${shiftTypeToggles.incidents ? 'Active' : 'Inactive'}`}
                  color={shiftTypeToggles.incidents ? 'success' : 'default'}
                />
                <Chip 
                  label={`Waakdienst: ${shiftTypeToggles.waakdienst ? 'Active' : 'Inactive'}`}
                  color={shiftTypeToggles.waakdienst ? 'success' : 'default'}
                />
                <Chip 
                  label={`Standby: ${shiftTypeToggles.incidents_standby ? 'Active' : 'Inactive'}`}
                  color={shiftTypeToggles.incidents_standby ? 'success' : 'default'}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ScheduleOrchestratorForm;
