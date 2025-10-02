import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Alert,
  Link,
  Divider,
} from '@mui/material';
import { Security, LockClock } from '@mui/icons-material';
import { apiClient } from '../../services/apiClient';

interface MFALoginProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (token: string) => void;
  userId?: number | null;
}

const MFALogin: React.FC<MFALoginProps> = ({ open, onClose, onSuccess, userId }) => {
  const [token, setToken] = useState('');
  const [useBackup, setUseBackup] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [backupCodesRemaining, setBackupCodesRemaining] = useState<number | null>(null);

  const handleVerify = async () => {
    if (token.length < 6) {
      setError('Please enter a valid code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response: any = await apiClient.post('/api/mfa/login/verify/', {
        token: token,
        use_backup: useBackup,
        user_id: userId, // Pass user_id from login response
      });

      // Handle both response.data and direct response formats
      const data = response.data || response;
      
      if (data.success && data.token) {
        // Store the token
        localStorage.setItem('token', data.token);
        
        if (data.backup_codes_remaining !== undefined) {
          setBackupCodesRemaining(data.backup_codes_remaining);
        }
        
        // Call success callback with token
        onSuccess(data.token);
      } else {
        setError('Verification failed. Please try again.');
      }
    } catch (err: any) {
      console.error('MFA Verification Error:', err);
      setError(err.response?.data?.error || err.data?.error || 'Invalid code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && token.length === (useBackup ? 8 : 6)) {
      handleVerify();
    }
  };

  const toggleBackupMode = () => {
    setUseBackup(!useBackup);
    setToken('');
    setError('');
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Security color="primary" fontSize="large" />
          <Typography variant="h5">Two-Factor Authentication</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}

          {backupCodesRemaining !== null && backupCodesRemaining < 3 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              Warning: You have only {backupCodesRemaining} backup code{backupCodesRemaining !== 1 ? 's' : ''} remaining.
              Please generate new codes from your security settings.
            </Alert>
          )}

          {!useBackup ? (
            <>
              <Typography variant="body1" gutterBottom>
                Enter the 6-digit code from your authenticator app
              </Typography>
              <TextField
                fullWidth
                label="Authentication Code"
                value={token}
                onChange={(e) => setToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
                onKeyPress={handleKeyPress}
                placeholder="000000"
                inputProps={{ 
                  maxLength: 6,
                  style: { 
                    fontSize: '28px', 
                    textAlign: 'center', 
                    letterSpacing: '12px',
                    fontFamily: 'monospace'
                  } 
                }}
                sx={{ my: 3 }}
                autoFocus
                helperText="Enter the current code displayed in your app"
              />
            </>
          ) : (
            <>
              <Typography variant="body1" gutterBottom>
                Enter one of your backup codes
              </Typography>
              <TextField
                fullWidth
                label="Backup Code"
                value={token}
                onChange={(e) => setToken(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8))}
                onKeyPress={handleKeyPress}
                placeholder="A1B2C3D4"
                inputProps={{ 
                  maxLength: 8,
                  style: { 
                    fontSize: '24px', 
                    textAlign: 'center', 
                    letterSpacing: '8px',
                    fontFamily: 'monospace'
                  } 
                }}
                sx={{ my: 3 }}
                autoFocus
                helperText="Each backup code can only be used once"
              />
            </>
          )}

          <Divider sx={{ my: 2 }} />

          <Box textAlign="center">
            <Link
              component="button"
              variant="body2"
              onClick={toggleBackupMode}
              sx={{ cursor: 'pointer' }}
            >
              {useBackup ? (
                <>
                  <LockClock sx={{ fontSize: 16, verticalAlign: 'middle', mr: 0.5 }} />
                  Use authenticator app instead
                </>
              ) : (
                'Lost your device? Use a backup code'
              )}
            </Link>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleVerify}
          disabled={loading || token.length < (useBackup ? 8 : 6)}
        >
          {loading ? 'Verifying...' : 'Verify'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MFALogin;
