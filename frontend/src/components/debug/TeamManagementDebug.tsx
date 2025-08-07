import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Alert } from '@mui/material';
import { apiClient } from '../../services/apiClient';
import { API_CONFIG } from '../../config/api';

const TeamManagementDebug: React.FC = () => {
  const [debugInfo, setDebugInfo] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const testAuthentication = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('Testing authentication...');
      const isAuth = apiClient.isAuthenticated();
      console.log('Is authenticated:', isAuth);
      
      const token = apiClient.getToken();
      console.log('Token:', token ? 'Present' : 'Missing');
      
      if (isAuth) {
        console.log('Testing user endpoint...');
        const user = await apiClient.getCurrentUser();
        console.log('Current user:', user);
      }
      
      setDebugInfo({
        isAuthenticated: isAuth,
        hasToken: !!token,
        token: token ? token.substring(0, 10) + '...' : null,
      });
    } catch (err) {
      console.error('Debug test error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const testTeamsEndpoint = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('Testing teams endpoint...');
      const teams = await apiClient.get(API_CONFIG.ENDPOINTS.TEAMS_LIST);
      console.log('Teams response:', teams);
      
      console.log('Testing departments endpoint...');
      const departments = await apiClient.get(API_CONFIG.ENDPOINTS.DEPARTMENTS_LIST);
      console.log('Departments response:', departments);
      
      setDebugInfo({
        teamsCount: Array.isArray(teams) ? teams.length : 'Not array',
        departmentsCount: Array.isArray(departments) ? departments.length : 'Not array',
        teamsData: teams,
        departmentsData: departments,
      });
    } catch (err) {
      console.error('Endpoint test error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    testAuthentication();
  }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Team Management Debug
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error: {error}
        </Alert>
      )}
      
      <Box sx={{ mb: 2 }}>
        <Button 
          variant="outlined" 
          onClick={testAuthentication} 
          disabled={loading}
          sx={{ mr: 2 }}
        >
          Test Authentication
        </Button>
        <Button 
          variant="outlined" 
          onClick={testTeamsEndpoint} 
          disabled={loading}
        >
          Test API Endpoints
        </Button>
      </Box>
      
      {debugInfo && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6">Debug Information:</Typography>
          <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px' }}>
            {JSON.stringify(debugInfo, null, 2)}
          </pre>
        </Box>
      )}
      
      {loading && (
        <Typography>Loading...</Typography>
      )}
    </Box>
  );
};

export default TeamManagementDebug;
