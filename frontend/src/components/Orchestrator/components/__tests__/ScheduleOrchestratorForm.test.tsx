import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../../test/utils';
import ScheduleOrchestratorForm from '../ScheduleOrchestratorForm';

describe('ScheduleOrchestratorForm', () => {
  beforeEach(() => {
    // Reset any mocks before each test
    jest.clearAllMocks();
  });

  describe('Form Rendering', () => {
    it('renders all main sections correctly', async () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Check for form title
      expect(screen.getByRole('heading', { name: /shift orchestrator/i })).toBeInTheDocument();

      // Check for section headings
      expect(screen.getByRole('heading', { name: /configuration/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /generate initial 6-month schedule/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /enable automatic weekly rolling/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /current status/i })).toBeInTheDocument();

      // Check for main action buttons
      expect(screen.getByRole('button', { name: /preview 6-month schedule/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /enable auto-scheduling/i })).toBeInTheDocument();
    });

    it('shows team selector with default selection', async () => {
      renderWithProviders(<ScheduleOrchestratorForm />);
      
      // Check for team selector and the team text content
      expect(screen.getByRole('combobox')).toBeInTheDocument();
      expect(screen.getByText('Team Alpha')).toBeInTheDocument();
    });

    it('shows shift type checkboxes', async () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Check for shift type checkboxes
      expect(screen.getByLabelText(/incidents \(mon-fri 8:00-17:00\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/waakdienst \(wed-wed on-call\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/incidents-standby \(backup\)/i)).toBeInTheDocument();
    });

    it('shows preview mode checkbox', async () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      expect(screen.getByLabelText(/preview mode \(dry run - no actual shifts created\)/i)).toBeInTheDocument();
    });

    it('enables generate button when shift types are selected by default', async () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Default state should have incidents and waakdienst selected, so button should be enabled
      const generateButton = screen.getByRole('button', { name: /preview 6-month schedule/i });
      expect(generateButton).toBeEnabled();
    });
  });

  describe('Form Interactions', () => {
    it('disables generate button when no shift types are selected', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      const generateButton = screen.getByRole('button', { name: /preview 6-month schedule/i });
      
      // Initially enabled with default selections
      expect(generateButton).toBeEnabled();

      // Uncheck all shift types
      const incidentsCheckbox = screen.getByRole('checkbox', { name: /incidents \(mon-fri 8:00-17:00\)/i });
      const waakdienstCheckbox = screen.getByRole('checkbox', { name: /waakdienst \(wed-wed on-call\)/i });
      
      await user.click(incidentsCheckbox);
      await user.click(waakdienstCheckbox);

      // Now button should be disabled
      expect(generateButton).toBeDisabled();
    });

    it('toggles shift type checkboxes correctly', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      const incidentsCheckbox = screen.getByRole('checkbox', { name: /incidents \(mon-fri 8:00-17:00\)/i });
      const waakdienstCheckbox = screen.getByRole('checkbox', { name: /waakdienst \(wed-wed on-call\)/i });
      const standbyCheckbox = screen.getByRole('checkbox', { name: /incidents-standby \(backup\)/i });

      // Initially incidents and waakdienst should be checked, standby unchecked
      expect(incidentsCheckbox).toBeChecked();
      expect(waakdienstCheckbox).toBeChecked();
      expect(standbyCheckbox).not.toBeChecked();

      // Toggle checkboxes
      await user.click(incidentsCheckbox);
      await user.click(standbyCheckbox);

      expect(incidentsCheckbox).not.toBeChecked();
      expect(waakdienstCheckbox).toBeChecked();
      expect(standbyCheckbox).toBeChecked();
    });

    it('toggles preview mode correctly', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      const previewCheckbox = screen.getByRole('checkbox', { name: /preview mode \(dry run - no actual shifts created\)/i });
      
      // Initially checked (dry run is default)
      expect(previewCheckbox).toBeChecked();

      // Toggle preview mode off
      await user.click(previewCheckbox);
      expect(previewCheckbox).not.toBeChecked();

      // Button text should change
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /generate 6-month schedule/i })).toBeInTheDocument();
      });

      // Toggle back on
      await user.click(previewCheckbox);
      expect(previewCheckbox).toBeChecked();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /preview 6-month schedule/i })).toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('has generate and auto-scheduling buttons available', async () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      const generateButton = screen.getByRole('button', { name: /preview 6-month schedule/i });
      const autoButton = screen.getByRole('button', { name: /enable auto-scheduling/i });

      // Both buttons should be present and enabled
      expect(generateButton).toBeEnabled();
      expect(autoButton).toBeEnabled();
    });

    it('shows correct button text based on preview mode', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Initially in preview mode
      expect(screen.getByRole('button', { name: /preview 6-month schedule/i })).toBeInTheDocument();

      // Toggle preview mode off
      const previewCheckbox = screen.getByRole('checkbox', { name: /preview mode/i });
      await user.click(previewCheckbox);

      // Button text should change
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /generate 6-month schedule/i })).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and accessible elements', async () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Check team selector has proper role
      expect(screen.getByRole('combobox')).toBeInTheDocument();
      
      // Check checkboxes have proper labels
      expect(screen.getByRole('checkbox', { name: /incidents \(mon-fri 8:00-17:00\)/i })).toBeInTheDocument();
      expect(screen.getByRole('checkbox', { name: /waakdienst \(wed-wed on-call\)/i })).toBeInTheDocument();
      expect(screen.getByRole('checkbox', { name: /incidents-standby \(backup\)/i })).toBeInTheDocument();
      expect(screen.getByRole('checkbox', { name: /preview mode/i })).toBeInTheDocument();
      
      // Check buttons have proper roles and accessible names
      expect(screen.getByRole('button', { name: /preview 6-month schedule/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /enable auto-scheduling/i })).toBeInTheDocument();
    });

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Tab to first focusable element (team selector)
      await user.tab();
      expect(screen.getByRole('combobox')).toHaveFocus();

      // Continue tabbing through checkboxes - be more specific to avoid multiple matches
      await user.tab();
      expect(screen.getByRole('checkbox', { name: /incidents \(mon-fri 8:00-17:00\)/i })).toHaveFocus();

      await user.tab();
      expect(screen.getByRole('checkbox', { name: /waakdienst \(wed-wed on-call\)/i })).toHaveFocus();
    });
  });
});
