import React, { useEffect, useState } from 'react';
import {
  Paper,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Button,
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon } from '@mui/icons-material';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../services/apiClient';

interface VerifyResponse {
  success: boolean;
  message: string;
  username?: string;
}

type VerificationStatus = 'loading' | 'success' | 'error' | 'invalid';

const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<VerificationStatus>('loading');
  const [message, setMessage] = useState<string>('');
  const [username, setUsername] = useState<string>('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('invalid');
      setMessage('No verification token provided.');
      return;
    }

    verifyEmail(token);
  }, [searchParams]);

  const verifyEmail = async (token: string) => {
    try {
      const response = await apiClient.post<VerifyResponse>('/api/auth/verify-email/', {
        token,
      });

      if (response.success) {
        setStatus('success');
        setMessage(response.message);
        setUsername(response.username || '');
        
        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      } else {
        setStatus('error');
        setMessage(response.message || 'Verification failed.');
      }
    } catch (err: any) {
      setStatus('error');
      const errorMessage = err.data?.error || err.data?.message || err.message || 'Verification failed. The link may be invalid or expired.';
      setMessage(errorMessage);
    }
  };

  const handleResendVerification = () => {
    // TODO: Implement resend verification
    // For now, just redirect to login
    navigate('/login');
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      sx={{ backgroundColor: 'background.default' }}
    >
      <Paper
        elevation={3}
        sx={{
          p: 4,
          maxWidth: 500,
          width: '100%',
          mx: 2,
          textAlign: 'center',
        }}
      >
        <Typography variant="h4" component="h1" gutterBottom>
          Email Verification
        </Typography>

        {status === 'loading' && (
          <Box sx={{ py: 4 }}>
            <CircularProgress size={60} />
            <Typography variant="body1" sx={{ mt: 3 }} color="text.secondary">
              Verifying your email address...
            </Typography>
          </Box>
        )}

        {status === 'success' && (
          <Box sx={{ py: 3 }}>
            <CheckCircle
              sx={{
                fontSize: 80,
                color: 'success.main',
                mb: 2,
              }}
            />
            <Alert severity="success" sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Email Verified Successfully!
              </Typography>
              <Typography variant="body2">
                {message}
              </Typography>
              {username && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Welcome, <strong>{username}</strong>!
                </Typography>
              )}
            </Alert>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Redirecting to login in 3 seconds...
            </Typography>
            <Button
              variant="contained"
              onClick={() => navigate('/login')}
              sx={{ mt: 2 }}
            >
              Go to Login Now
            </Button>
          </Box>
        )}

        {status === 'error' && (
          <Box sx={{ py: 3 }}>
            <ErrorIcon
              sx={{
                fontSize: 80,
                color: 'error.main',
                mb: 2,
              }}
            />
            <Alert severity="error" sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Verification Failed
              </Typography>
              <Typography variant="body2">
                {message}
              </Typography>
            </Alert>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2, mb: 2 }}>
              The verification link may have expired or is invalid.
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button
                variant="outlined"
                onClick={handleResendVerification}
              >
                Request New Link
              </Button>
              <Button
                variant="contained"
                onClick={() => navigate('/login')}
              >
                Go to Login
              </Button>
            </Box>
          </Box>
        )}

        {status === 'invalid' && (
          <Box sx={{ py: 3 }}>
            <ErrorIcon
              sx={{
                fontSize: 80,
                color: 'warning.main',
                mb: 2,
              }}
            />
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Invalid Link
              </Typography>
              <Typography variant="body2">
                {message}
              </Typography>
            </Alert>
            <Button
              variant="contained"
              onClick={() => navigate('/login')}
              sx={{ mt: 2 }}
            >
              Go to Login
            </Button>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default VerifyEmail;
