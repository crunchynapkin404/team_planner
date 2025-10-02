import React, { useState } from 'react';
import {
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Link,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/authService';
import { LoginCredentials } from '../../types';
import MFALogin from './MFALogin';

const LoginForm: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showMFADialog, setShowMFADialog] = useState(false);
  const [mfaUserId, setMfaUserId] = useState<number | null>(null);
  
  const [credentials, setCredentials] = useState<LoginCredentials>({
    username: '',
    password: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setCredentials(prev => ({
      ...prev,
      [name]: value,
    }));
    
    // Clear errors when user starts typing
    if (error) {
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await authService.login(credentials);
      
      if (response.mfa_required) {
        // MFA is required - show MFA dialog
        setMfaUserId(response.user_id || null);
        setShowMFADialog(true);
        setIsLoading(false);
      } else {
        // No MFA - redirect to dashboard
        window.location.href = '/dashboard';
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please try again.');
      setIsLoading(false);
    }
  };

  const handleMFASuccess = () => {
    // MFA verified successfully - redirect to dashboard
    window.location.href = '/dashboard';
  };

  const handleMFAClose = () => {
    setShowMFADialog(false);
    setMfaUserId(null);
    setIsLoading(false);
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
          maxWidth: 400,
          width: '100%',
          mx: 2,
        }}
      >
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Team Planner
        </Typography>
        <Typography variant="h6" component="h2" gutterBottom align="center" color="text.secondary">
          Sign In
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
          <TextField
            fullWidth
            label="Username"
            name="username"
            value={credentials.username}
            onChange={handleChange}
            margin="normal"
            required
            autoFocus
            disabled={isLoading}
          />
          <TextField
            fullWidth
            label="Password"
            name="password"
            type="password"
            value={credentials.password}
            onChange={handleChange}
            margin="normal"
            required
            disabled={isLoading}
          />
          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2 }}
            disabled={isLoading}
            startIcon={isLoading ? <CircularProgress size={20} /> : null}
          >
            {isLoading ? 'Signing In...' : 'Sign In'}
          </Button>

          <Typography variant="body2" align="center" sx={{ mt: 2 }}>
            Don't have an account?{' '}
            <Link
              component="button"
              variant="body2"
              onClick={(e) => {
                e.preventDefault();
                navigate('/register');
              }}
              sx={{ cursor: 'pointer' }}
            >
              Create one
            </Link>
          </Typography>
        </Box>
      </Paper>
      
      {/* MFA Dialog */}
      <MFALogin
        open={showMFADialog}
        onClose={handleMFAClose}
        onSuccess={handleMFASuccess}
        userId={mfaUserId}
      />
    </Box>
  );
};

export default LoginForm;
