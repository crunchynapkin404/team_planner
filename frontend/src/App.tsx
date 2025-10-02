import { Routes, Route, Navigate } from 'react-router-dom';
import { apiClient } from './services/apiClient';
import LoginForm from './components/auth/LoginForm';
import PrivateRoute from './components/auth/PrivateRoute';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard';
import CalendarPage from './pages/CalendarPage';
import TimelinePage from './pages/TimelinePage';
import UnifiedOrchestratorPage from './pages/UnifiedOrchestratorPage';
import FairnessDashboard from './pages/FairnessDashboard';
import UserManagement from './pages/UserManagement';
import TeamManagement from './pages/TeamManagement';
import ProfileManagement from './pages/ProfileManagement';
import ShiftSwapsPage from './pages/ShiftSwapsPage';
import LeaveRequestPage from './pages/LeaveRequestPage';
import ConflictResolutionPage from './pages/ConflictResolutionPage';
import ReportsDashboard from './pages/ReportsDashboard';
import UnifiedManagement from './pages/UnifiedManagement';
import RecurringPatternsPage from './pages/RecurringPatternsPage';
import ShiftTemplateLibrary from './pages/ShiftTemplateLibrary';
import BulkShiftOperations from './pages/BulkShiftOperations';
import ApprovalRulesPage from './pages/ApprovalRulesPage';
import PendingApprovalsPage from './pages/PendingApprovalsPage';

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
              <UserManagement />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/user-management"
        element={
          <PrivateRoute>
            <MainLayout>
              <UserManagement />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/team-management"
        element={
          <PrivateRoute>
            <MainLayout>
              <TeamManagement />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/teams"
        element={
          <PrivateRoute>
            <MainLayout>
              <TeamManagement />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/management"
        element={
          <PrivateRoute>
            <MainLayout>
              <UnifiedManagement />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/profile"
        element={
          <PrivateRoute>
            <MainLayout>
              <ProfileManagement />
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
              <UnifiedOrchestratorPage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/orchestrator-dashboard"
        element={
          <PrivateRoute>
            <MainLayout>
              <UnifiedOrchestratorPage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/reports"
        element={
          <PrivateRoute>
            <MainLayout>
              <ReportsDashboard />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/patterns"
        element={
          <PrivateRoute>
            <MainLayout>
              <RecurringPatternsPage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/templates"
        element={
          <PrivateRoute>
            <MainLayout>
              <ShiftTemplateLibrary />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/bulk-operations"
        element={
          <PrivateRoute>
            <MainLayout>
              <BulkShiftOperations />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/fairness"
        element={
          <PrivateRoute>
            <MainLayout>
              <FairnessDashboard />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/orchestrator-history"
        element={
          <PrivateRoute>
            <MainLayout>
              <UnifiedOrchestratorPage />
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
              <ShiftSwapsPage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/leaves"
        element={
          <PrivateRoute>
            <MainLayout>
              <LeaveRequestPage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/leave-conflicts"
        element={
          <PrivateRoute>
            <MainLayout>
              <ConflictResolutionPage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/approval-rules"
        element={
          <PrivateRoute>
            <MainLayout>
              <ApprovalRulesPage />
            </MainLayout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/pending-approvals"
        element={
          <PrivateRoute>
            <MainLayout>
              <PendingApprovalsPage />
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
