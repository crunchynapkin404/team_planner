import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { apiClient } from './services/apiClient';
import LoginForm from './components/auth/LoginForm';
import PrivateRoute from './components/auth/PrivateRoute';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard';
import CalendarPage from './pages/CalendarPage';
import TimelinePage from './pages/TimelinePage';
import OrchestratorPage from './pages/OrchestratorPage';

function App() {
  const isAuthenticated = apiClient.isAuthenticated();

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <LoginForm />
          )
        }
      />
      
      {/* Protected routes */}
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <MainLayout>
              <Dashboard />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      {/* Placeholder routes for future development */}
      <Route
        path="/employees"
        element={
          <PrivateRoute>
            <MainLayout>
              <div>Employees page coming soon...</div>
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/calendar"
        element={
          <PrivateRoute>
            <MainLayout>
              <CalendarPage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/timeline"
        element={
          <PrivateRoute>
            <MainLayout>
              <TimelinePage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/orchestrator"
        element={
          <PrivateRoute>
            <MainLayout>
              <OrchestratorPage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      {/* Redirect old schedules route to calendar */}
      <Route
        path="/schedules"
        element={<Navigate to="/calendar" replace />}
      />
      
      <Route
        path="/swaps"
        element={
          <PrivateRoute>
            <MainLayout>
              <div>Shift Swaps page coming soon...</div>
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/leaves"
        element={
          <PrivateRoute>
            <MainLayout>
              <div>Leave Requests page coming soon...</div>
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/settings"
        element={
          <PrivateRoute>
            <MainLayout>
              <div>Settings page coming soon...</div>
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      {/* Default redirect */}
      <Route
        path="/"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      
      {/* Catch-all route */}
      <Route
        path="*"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  );
}

export default App;
