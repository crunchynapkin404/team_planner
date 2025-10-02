import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Stepper,
  Step,
  StepLabel,
  Alert,
  Chip,
  Grid,
  Paper,
} from '@mui/material';
import { Security, VpnKey, Download, ContentCopy } from '@mui/icons-material';
import { apiClient } from '../../services/apiClient';

interface MFASetupProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const MFASetup: React.FC<MFASetupProps> = ({ open, onClose, onSuccess }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [qrCode, setQrCode] = useState('');
  const [secret, setSecret] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [verificationToken, setVerificationToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const steps = ['Scan QR Code', 'Verify Token', 'Save Backup Codes'];

  useEffect(() => {
    if (open) {
      initializeMFA();
    }
  }, [open]);

  const initializeMFA = async () => {
    setLoading(true);
    setError('');
    try {
      const response: any = await apiClient.post('/api/mfa/setup/');
      console.log('MFA Setup Response:', response);
      
      // Handle both response.data and direct response formats
      const data = response.data || response;
      
      if (!data.qr_code || !data.secret || !data.backup_codes) {
        console.error('Invalid response data:', data);
        throw new Error('Invalid response format from server');
      }
      
      setQrCode(data.qr_code);
      setSecret(data.secret);
      setBackupCodes(data.backup_codes);
      setActiveStep(0);
      setError('');
    } catch (err: any) {
      console.error('MFA Setup Error:', err);
      const errorMessage = err.response?.data?.error 
        || err.response?.data?.detail
        || err.message 
        || 'Failed to initialize MFA';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const verifyToken = async () => {
    setLoading(true);
    setError('');
    try {
      await apiClient.post('/api/mfa/verify/', {
        token: verificationToken,
      });
      setActiveStep(2);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Invalid token');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = () => {
    onSuccess();
    onClose();
  };

  const handleNext = () => {
    if (activeStep === 0) {
      setActiveStep(1);
    } else if (activeStep === 1) {
      verifyToken();
    } else {
      handleComplete();
    }
  };

  const handleBack = () => {
    setActiveStep(activeStep - 1);
  };

  const copyToClipboard = (text: string) => {
    // Fallback for environments where clipboard API is not available
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch((err) => {
        console.error('Failed to copy to clipboard:', err);
        fallbackCopyToClipboard(text);
      });
    } else {
      fallbackCopyToClipboard(text);
    }
  };

  const fallbackCopyToClipboard = (text: string) => {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
    } catch (err) {
      console.error('Fallback copy failed:', err);
    }
    document.body.removeChild(textArea);
  };

  const downloadBackupCodes = () => {
    const element = document.createElement('a');
    const file = new Blob([backupCodes.join('\n')], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = 'team-planner-backup-codes.txt';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Security color="primary" fontSize="large" />
          <Typography variant="h5">Enable Two-Factor Authentication</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 3, mt: 2 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* Step 1: QR Code */}
        {activeStep === 0 && (
          <Box textAlign="center">
            <Typography variant="body1" gutterBottom>
              Scan this QR code with your authenticator app
            </Typography>
            <Typography variant="caption" display="block" gutterBottom color="text.secondary">
              (Google Authenticator, Authy, Microsoft Authenticator, etc.)
            </Typography>
            {qrCode && (
              <Paper elevation={3} sx={{ display: 'inline-block', p: 2, my: 2 }}>
                <img src={qrCode} alt="MFA QR Code" style={{ maxWidth: '280px', display: 'block' }} />
              </Paper>
            )}
            <Typography variant="body2" color="textSecondary" gutterBottom sx={{ mt: 3 }}>
              Or enter this key manually:
            </Typography>
            <Box display="flex" alignItems="center" justifyContent="center" gap={1} sx={{ mt: 1 }}>
              <Chip 
                label={secret} 
                icon={<VpnKey />}
                sx={{ fontFamily: 'monospace', fontSize: '14px', cursor: 'pointer' }}
                onClick={() => copyToClipboard(secret)}
              />
              <Button 
                size="small" 
                startIcon={<ContentCopy />}
                onClick={() => copyToClipboard(secret)}
              >
                Copy
              </Button>
            </Box>
          </Box>
        )}

        {/* Step 2: Verify */}
        {activeStep === 1 && (
          <Box>
            <Typography variant="body1" gutterBottom sx={{ mb: 3 }}>
              Enter the 6-digit code from your authenticator app to verify setup
            </Typography>
            <TextField
              fullWidth
              label="Verification Code"
              value={verificationToken}
              onChange={(e) => setVerificationToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
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
              sx={{ my: 2 }}
              autoFocus
              helperText="Enter the current code displayed in your authenticator app"
            />
          </Box>
        )}

        {/* Step 3: Backup Codes */}
        {activeStep === 2 && (
          <Box>
            <Alert severity="warning" sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                <strong>Important!</strong> Save these backup codes in a secure place.
              </Typography>
              <Typography variant="body2">
                You can use them to access your account if you lose your authenticator device.
                Each code can only be used once.
              </Typography>
            </Alert>
            <Grid container spacing={1}>
              {backupCodes.map((code, index) => (
                <Grid item xs={6} key={index}>
                  <Paper 
                    elevation={1} 
                    sx={{ 
                      p: 1.5, 
                      textAlign: 'center',
                      backgroundColor: 'grey.100',
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: 'grey.200',
                      }
                    }}
                    onClick={() => copyToClipboard(code)}
                  >
                    <Typography 
                      sx={{ 
                        fontFamily: 'monospace', 
                        fontSize: '16px',
                        fontWeight: 'medium'
                      }}
                    >
                      {code}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
            <Box mt={3} display="flex" gap={1}>
              <Button
                variant="outlined"
                startIcon={<ContentCopy />}
                onClick={() => copyToClipboard(backupCodes.join('\n'))}
                fullWidth
              >
                Copy All Codes
              </Button>
              <Button
                variant="outlined"
                startIcon={<Download />}
                onClick={downloadBackupCodes}
                fullWidth
              >
                Download as File
              </Button>
            </Box>
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        {activeStep > 0 && activeStep < 2 && (
          <Button onClick={handleBack} disabled={loading}>
            Back
          </Button>
        )}
        <Button
          variant="contained"
          onClick={handleNext}
          disabled={loading || (activeStep === 1 && verificationToken.length !== 6)}
        >
          {loading ? 'Processing...' : (activeStep === 2 ? 'Finish' : 'Next')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MFASetup;
