// MSW Server setup for testing
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Setup MSW server with default handlers
export const server = setupServer(...handlers);

// Helper to add additional handlers for specific tests
export const addHandlers = (...additionalHandlers: any[]) => {
  server.use(...additionalHandlers);
};

// Helper to reset handlers to default
export const resetHandlers = () => {
  server.resetHandlers(...handlers);
};
