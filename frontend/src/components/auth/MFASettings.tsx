import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  Security,
  CheckCircle,
  Warning,
  VpnKey,
  History,
  Refresh,
} from '@mui/icons-material';
import { apiClient } from '../../services/apiClient';
import MFASetup from './MFASetup';

interface MFAStatus {
  enabled: boolean;
  verified: boolean;
  device_name?: string;
  last_used?: string;
  backup_codes_remaining?: number;
}

const MFASettings: React.FC = () => {
  const [mfaStatus, setMFAStatus] = useState<MFAStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [setupDialogOpen, setSetupDialogOpen] = useState(false);
  const [disableDialogOpen, setDisableDialogOpen] = useState(false);
  const [regenerateDialogOpen, setRegenerateDialogOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [newBackupCodes, setNewBackupCodes] = useState<string[]>([]);

  useEffect(() => {
    fetchMFAStatus();
  }, []);

  const fetchMFAStatus = async () => {
    setLoading(true);
    try {
      const response: any = await apiClient.get('/api/mfa/status/');
      const data = response.data || response;
      setMFAStatus(data);
    } catch (err) {
      console.error('Failed to fetch MFA status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSetupSuccess = () => {
    setSetupDialogOpen(false);
    setSuccess('Two-factor authentication has been enabled successfully!');
    fetchMFAStatus();
  };

  const handleDisableMFA = async () => {
    setError('');
    try {
      await apiClient.post('/api/mfa/disable/', {
        password,
        token,
      });
      setDisableDialogOpen(false);
      setPassword('');
      setToken('');
      setSuccess('Two-factor authentication has been disabled.');
      fetchMFAStatus();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to disable MFA');
    }
  };

  const handleRegenerateBackupCodes = async () => {
    setError('');
    try {
      const response: any = await apiClient.post('/api/mfa/backup-codes/regenerate/', {
        password,
        token,
      });
      setNewBackupCodes(response.data.backup_codes);
      setPassword('');
      setToken('');
      setSuccess('New backup codes have been generated.');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to regenerate codes');
    }
  };

  const downloadBackupCodes = () => {
    const element = document.createElement('a');
    const file = new Blob([newBackupCodes.join('\n')], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = 'team-planner-backup-codes-new.txt';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const copyBackupCodes = () => {
    navigator.clipboard.writeText(newBackupCodes.join('\n'));
  };

  if (loading) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Box>
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
            <Box display="flex" alignItems="center" gap={1}>
              <Security color="primary" fontSize="large" />
              <Typography variant="h6">Two-Factor Authentication</Typography>
            </Box>
            {mfaStatus?.enabled && mfaStatus?.verified && (
              <Chip
                icon={<CheckCircle />}
                label="Enabled"
                color="success"
                size="small"
              />
            )}
          </Box>

          {success && (
            <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
              {success}
            </Alert>
          )}

          <Typography variant="body2" color="text.secondary" paragraph>
            Two-factor authentication adds an extra layer of security to your account.
            You'll need to enter a code from your authenticator app when you sign in.
          </Typography>

          {!mfaStatus?.enabled || !mfaStatus?.verified ? (
            <Button
              variant="contained"
              startIcon={<Security />}
              onClick={() => setSetupDialogOpen(true)}
              fullWidth
            >
              Enable Two-Factor Authentication
            </Button>
          ) : (
            <Box>
              <List>
                <ListItem>
                  <ListItemIcon>
                    <VpnKey />
                  </ListItemIcon>
                  <ListItemText
                    primary="Device"
                    secondary={mfaStatus.device_name || 'Authenticator App'}
                  />
                </ListItem>
                
                {mfaStatus.last_used && (
                  <ListItem>
                    <ListItemIcon>
                      <History />
                    </ListItemIcon>
                    <ListItemText
                      primary="Last Used"
                      secondary={new Date(mfaStatus.last_used).toLocaleString()}
                    />
                  </ListItem>
                )}

                <ListItem>
                  <ListItemIcon>
                    {(mfaStatus.backup_codes_remaining || 0) < 3 ? <Warning color="warning" /> : <CheckCircle />}
                  </ListItemIcon>
                  <ListItemText
                    primary="Backup Codes"
                    secondary={`${mfaStatus.backup_codes_remaining || 0} remaining`}
                  />
                </ListItem>
              </List>

              {(mfaStatus.backup_codes_remaining || 0) < 3 && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  You're running low on backup codes. Generate new ones to ensure you can access your account.
                </Alert>
              )}

              <Divider sx={{ my: 2 }} />

              <Box display="flex" gap={1} flexWrap="wrap">
                <Button
                  variant="outlined"
                  startIcon={<Refresh />}
                  onClick={() => setRegenerateDialogOpen(true)}
                >
                  Regenerate Backup Codes
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={() => setDisableDialogOpen(true)}
                >
                  Disable MFA
                </Button>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* MFA Setup Dialog */}
      <MFASetup
        open={setupDialogOpen}
        onClose={() => setSetupDialogOpen(false)}
        onSuccess={handleSetupSuccess}
      />

      {/* Disable MFA Dialog */}
      <Dialog open={disableDialogOpen} onClose={() => setDisableDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Disable Two-Factor Authentication</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <Typography variant="body2" paragraph>
            To disable two-factor authentication, please enter your password and current authentication code.
          </Typography>
          <TextField
            fullWidth
            type="password"
            label="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Authentication Code"
            value={token}
            onChange={(e) => setToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            inputProps={{ maxLength: 6 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setDisableDialogOpen(false);
            setPassword('');
            setToken('');
            setError('');
          }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDisableMFA}
            disabled={!password || token.length !== 6}
          >
            Disable MFA
          </Button>
        </DialogActions>
      </Dialog>

      {/* Regenerate Backup Codes Dialog */}
      <Dialog open={regenerateDialogOpen} onClose={() => {
        setRegenerateDialogOpen(false);
        setNewBackupCodes([]);
        setPassword('');
        setToken('');
        setError('');
      }} maxWidth="sm" fullWidth>
        <DialogTitle>Regenerate Backup Codes</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          
          {newBackupCodes.length === 0 ? (
            <>
              <Alert severity="warning" sx={{ mb: 2 }}>
                This will invalidate all your existing backup codes. Save the new codes in a secure place.
              </Alert>
              <TextField
                fullWidth
                type="password"
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Authentication Code"
                value={token}
                onChange={(e) => setToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                inputProps={{ maxLength: 6 }}
              />
            </>
          ) : (
            <Box>
              <Alert severity="success" sx={{ mb: 2 }}>
                New backup codes generated successfully! Save these in a secure place.
              </Alert>
              <Box sx={{ backgroundColor: 'grey.100', p: 2, borderRadius: 1, mb: 2 }}>
                {newBackupCodes.map((code, index) => (
                  <Typography key={index} sx={{ fontFamily: 'monospace', fontSize: '14px' }}>
                    {code}
                  </Typography>
                ))}
              </Box>
              <Box display="flex" gap={1}>
                <Button variant="outlined" onClick={copyBackupCodes} fullWidth>
                  Copy All
                </Button>
                <Button variant="outlined" onClick={downloadBackupCodes} fullWidth>
                  Download
                </Button>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setRegenerateDialogOpen(false);
            setNewBackupCodes([]);
            setPassword('');
            setToken('');
            setError('');
          }}>
            {newBackupCodes.length > 0 ? 'Close' : 'Cancel'}
          </Button>
          {newBackupCodes.length === 0 && (
            <Button
              variant="contained"
              onClick={handleRegenerateBackupCodes}
              disabled={!password || token.length !== 6}
            >
              Generate New Codes
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MFASettings;
