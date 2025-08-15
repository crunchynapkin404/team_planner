/**
 * Availability Checker - Shows employee availability for shifts
 */

import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Avatar,
} from '@mui/material';
import { People, Person, CheckCircle, Cancel } from '@mui/icons-material';
import { useOrchestrator } from '../../../hooks/useOrchestrator';

const AvailabilityChecker: React.FC = () => {
  const { getAvailabilityForCurrentWeek, getAvailability, state } = useOrchestrator();

  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    shiftType: '',
    departmentId: '',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const handleQuickCheck = async () => {
    setIsLoading(true);
    try {
      await getAvailabilityForCurrentWeek(filters.shiftType || undefined);
    } catch (error) {
      console.error('Failed to get availability:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomCheck = async () => {
    if (!filters.startDate || !filters.endDate) return;

    setIsLoading(true);
    try {
      await getAvailability({
        start_date: filters.startDate,
        end_date: filters.endDate,
        shift_type: filters.shiftType || undefined as any,
        department_id: filters.departmentId || undefined,
      });
    } catch (error) {
      console.error('Failed to get availability:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getAvailabilityIcon = (employee: any) => {
    const hasIncidents = employee.available_for_incidents;
    const hasWaakdienst = employee.available_for_waakdienst;
    
    if (hasIncidents && hasWaakdienst) {
      return <CheckCircle color="success" />;
    } else if (hasIncidents || hasWaakdienst) {
      return <CheckCircle color="warning" />;
    } else {
      return <Cancel color="error" />;
    }
  };

  const getAvailabilityText = (employee: any) => {
    const types = [];
    if (employee.available_for_incidents) types.push('Incidents');
    if (employee.available_for_waakdienst) types.push('Waakdienst');
    return types.length > 0 ? types.join(', ') : 'Not available';
  };

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <People color="primary" />
        Employee Availability
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Check employee availability for different shift types and time periods
      </Typography>

      <Grid container spacing={3}>
        {/* Quick Check */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Availability Check
              </Typography>
              <Grid container spacing={2} alignItems="end">
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Shift Type</InputLabel>
                    <Select
                      value={filters.shiftType}
                      label="Shift Type"
                      onChange={(e) => handleFilterChange('shiftType', e.target.value)}
                    >
                      <MenuItem value="">All Types</MenuItem>
                      <MenuItem value="incidents">Incidents</MenuItem>
                      <MenuItem value="waakdienst">Waakdienst</MenuItem>
                      <MenuItem value="incidents_standby">Incidents Standby</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Button
                    fullWidth
                    variant="contained"
                    onClick={handleQuickCheck}
                    disabled={isLoading}
                  >
                    Check Current Week
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Custom Filters */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Custom Availability Check
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    label="Start Date"
                    type="date"
                    value={filters.startDate}
                    onChange={(e) => handleFilterChange('startDate', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    label="End Date"
                    type="date"
                    value={filters.endDate}
                    onChange={(e) => handleFilterChange('endDate', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <FormControl fullWidth>
                    <InputLabel>Department</InputLabel>
                    <Select
                      value={filters.departmentId}
                      label="Department"
                      onChange={(e) => handleFilterChange('departmentId', e.target.value)}
                    >
                      <MenuItem value="">All Departments</MenuItem>
                      <MenuItem value="1">Department 1</MenuItem>
                      <MenuItem value="2">Department 2</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    fullWidth
                    variant="contained"
                    onClick={handleCustomCheck}
                    disabled={isLoading || !filters.startDate || !filters.endDate}
                    sx={{ height: '56px' }}
                  >
                    Check Availability
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Loading */}
        {isLoading && (
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          </Grid>
        )}

        {/* Results */}
        {state.availabilityData.length > 0 && !isLoading && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                  <Typography variant="h6">
                    Available Employees ({state.availabilityData.length})
                  </Typography>
                  <Chip 
                    label={`${state.availabilityData.length} available`}
                    color="primary"
                  />
                </Box>
                
                <List>
                  {state.availabilityData.map((employee) => (
                    <ListItem key={employee.employee_id} divider>
                      <ListItemIcon>
                        <Avatar>
                          <Person />
                        </Avatar>
                      </ListItemIcon>
                      <ListItemText
                        primary={employee.name}
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              {employee.email}
                            </Typography>
                            <Typography variant="body2">
                              Available for: {getAvailabilityText(employee)}
                            </Typography>
                            {employee.current_assignments_count > 0 && (
                              <Typography variant="body2" color="text.secondary">
                                Current assignments: {employee.current_assignments_count}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getAvailabilityIcon(employee)}
                        {employee.fairness_score && (
                          <Chip
                            label={`Score: ${employee.fairness_score.toFixed(1)}`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                      </Box>
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        )}

        {state.availabilityData.length === 0 && !isLoading && (
          <Grid item xs={12}>
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No availability data available. Use the check buttons above to load employee availability.
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default AvailabilityChecker;
