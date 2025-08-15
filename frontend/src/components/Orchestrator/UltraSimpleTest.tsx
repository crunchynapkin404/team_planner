/**
 * Ultra Simple Test - No API calls, just basic UI
 */

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  FormControlLabel,
  Checkbox,
  Card,
  CardContent,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';

const UltraSimpleTest: React.FC = () => {
  const [dryRun, setDryRun] = useState(true);
  const [selectedTeam, setSelectedTeam] = useState(1);
  const [selectedShiftTypes, setSelectedShiftTypes] = useState<string[]>(['incidents', 'waakdienst']);

  const handleShiftTypeChange = (shiftType: string, checked: boolean) => {
    if (checked) {
      setSelectedShiftTypes(prev => [...prev, shiftType]);
    } else {
      setSelectedShiftTypes(prev => prev.filter(type => type !== shiftType));
    }
  };

  const handleGenerate = () => {
    alert(`Would generate for Team ${selectedTeam} with shift types: ${selectedShiftTypes.join(', ')}`);
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 4 }}>
      <Typography variant="h4" gutterBottom>
        Ultra Simple Orchestrator Test
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Basic form with no API calls - just to test rendering
      </Typography>

      <Grid container spacing={3}>
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
                      value={selectedTeam}
                      label="Team"
                      onChange={(e) => setSelectedTeam(e.target.value as number)}
                    >
                      <MenuItem value={1}>Team 1</MenuItem>
                      <MenuItem value={2}>Team 2</MenuItem>
                      <MenuItem value={3}>Team 3</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Shift Types:
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedShiftTypes.includes('incidents')}
                          onChange={(e) => handleShiftTypeChange('incidents', e.target.checked)}
                        />
                      }
                      label="Incidents"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedShiftTypes.includes('waakdienst')}
                          onChange={(e) => handleShiftTypeChange('waakdienst', e.target.checked)}
                        />
                      }
                      label="Waakdienst"
                    />
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Generate Schedule
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={dryRun}
                      onChange={(e) => setDryRun(e.target.checked)}
                    />
                  }
                  label="Preview Mode (dry run)"
                />
              </Box>

              <Button
                variant="contained"
                size="large"
                onClick={handleGenerate}
                disabled={selectedShiftTypes.length === 0}
              >
                {dryRun ? 'Preview Schedule' : 'Generate Schedule'}
              </Button>
              
              {selectedShiftTypes.length === 0 && (
                <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                  Please select at least one shift type
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default UltraSimpleTest;
