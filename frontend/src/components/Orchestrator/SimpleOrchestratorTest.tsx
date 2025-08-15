/**
 * Simple Orchestrator Test - Direct render without dashboard
 */

import React from 'react';
import { Container, Typography } from '@mui/material';
import ScheduleOrchestratorForm from './components/ScheduleOrchestratorForm';

const SimpleOrchestratorTest: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Orchestrator Test
      </Typography>
      <ScheduleOrchestratorForm />
    </Container>
  );
};

export default SimpleOrchestratorTest;
