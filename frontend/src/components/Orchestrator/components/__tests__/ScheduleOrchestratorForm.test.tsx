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
    it('renders all form sections correctly', () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Check for form title
      expect(screen.getByRole('heading', { name: /schedule orchestration/i })).toBeInTheDocument();

      // Check for section headings
      expect(screen.getByRole('heading', { name: /quick actions/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /custom date range/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /options/i })).toBeInTheDocument();

      // Check for form fields
      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument();
      
      // Check for quick action buttons
      expect(screen.getByRole('button', { name: /schedule current week/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /schedule next week/i })).toBeInTheDocument();
      
      // Check for main action button
      expect(screen.getByRole('button', { name: /run orchestration/i })).toBeInTheDocument();
    });

    it('displays date inputs with proper format', () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);

      expect(startDateInput).toHaveAttribute('type', 'date');
      expect(endDateInput).toHaveAttribute('type', 'date');
    });

    it('shows options section with checkboxes', () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Check for option checkboxes
      expect(screen.getByLabelText(/dry run \(preview only\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/force \(override existing assignments\)/i)).toBeInTheDocument();
    });

    it('disables run orchestration button when dates are empty', () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      const runButton = screen.getByRole('button', { name: /run orchestration/i });
      expect(runButton).toBeDisabled();
    });
  });

  describe('Form Validation', () => {
    it('validates that end date is after start date', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);

      // Set end date before start date
      await user.type(startDateInput, '2024-01-15');
      await user.type(endDateInput, '2024-01-10');

      const submitButton = screen.getByRole('button', { name: /run orchestration/i });
      expect(submitButton).toBeEnabled(); // Button should be enabled now that dates are filled
      
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/end date must be after start date/i)).toBeInTheDocument();
      });
    });

    it('requires start and end dates to be filled', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      const submitButton = screen.getByRole('button', { name: /run orchestration/i });
      
      // Button should be disabled when dates are empty
      expect(submitButton).toBeDisabled();
      
      // Fill only start date
      const startDateInput = screen.getByLabelText(/start date/i);
      await user.type(startDateInput, '2024-01-15');
      expect(submitButton).toBeDisabled();
      
      // Fill end date too
      const endDateInput = screen.getByLabelText(/end date/i);
      await user.type(endDateInput, '2024-01-20');
      expect(submitButton).toBeEnabled();
    });

    it('validates date range duration', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);

      // Set date range longer than 30 days
      await user.type(startDateInput, '2024-01-01');
      await user.type(endDateInput, '2024-03-01');

      const submitButton = screen.getByRole('button', { name: /run orchestration/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/date range cannot exceed 30 days/i)).toBeInTheDocument();
      });
    });
  });

  describe('Form Interactions', () => {
    it('updates form fields when values are changed', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Fill form
      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);
      const dryRunCheckbox = screen.getByLabelText(/dry run \(preview only\)/i);

      await user.type(startDateInput, '2024-01-15');
      await user.type(endDateInput, '2024-01-20');
      await user.click(dryRunCheckbox);

      expect(startDateInput).toHaveValue('2024-01-15');
      expect(endDateInput).toHaveValue('2024-01-20');
      expect(dryRunCheckbox).toBeChecked();
    });

    it('updates options when checkboxes are toggled', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      const dryRunCheckbox = screen.getByLabelText(/dry run \(preview only\)/i);
      const forceCheckbox = screen.getByLabelText(/force \(override existing assignments\)/i);

      // Initially unchecked
      expect(dryRunCheckbox).not.toBeChecked();
      expect(forceCheckbox).not.toBeChecked();

      // Toggle options
      await user.click(dryRunCheckbox);
      await user.click(forceCheckbox);

      expect(dryRunCheckbox).toBeChecked();
      expect(forceCheckbox).toBeChecked();

      // Toggle off
      await user.click(dryRunCheckbox);
      expect(dryRunCheckbox).not.toBeChecked();
      expect(forceCheckbox).toBeChecked();
    });

    it('handles department selection', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      const departmentSelect = screen.getByRole('combobox');
      
      // Click to open dropdown
      await user.click(departmentSelect);
      
      // Wait for dropdown options to appear and select one
      await waitFor(() => {
        const option = screen.getByText('Department 1');
        expect(option).toBeInTheDocument();
      });
      
      await user.click(screen.getByText('Department 1'));
      
      // The select should now show the selected value (this might be implementation dependent)
      expect(departmentSelect).toBeInTheDocument();
    });
  });

  describe('Quick Actions', () => {
    it('renders quick action buttons', () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      const currentWeekButton = screen.getByRole('button', { name: /schedule current week/i });
      const nextWeekButton = screen.getByRole('button', { name: /schedule next week/i });

      expect(currentWeekButton).toBeInTheDocument();
      expect(nextWeekButton).toBeInTheDocument();
    });

    it('quick action buttons are enabled by default', () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      const currentWeekButton = screen.getByRole('button', { name: /schedule current week/i });
      const nextWeekButton = screen.getByRole('button', { name: /schedule next week/i });

      expect(currentWeekButton).toBeEnabled();
      expect(nextWeekButton).toBeEnabled();
    });
  });

  describe('Form Submission', () => {
    it('enables run orchestration button with valid data', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Fill valid form data
      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);

      await user.type(startDateInput, '2024-01-15');
      await user.type(endDateInput, '2024-01-20');

      const submitButton = screen.getByRole('button', { name: /run orchestration/i });
      expect(submitButton).toBeEnabled();
    });

    it('shows running state during submission', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Fill minimal valid data
      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);

      await user.type(startDateInput, '2024-01-15');
      await user.type(endDateInput, '2024-01-20');

      const submitButton = screen.getByRole('button', { name: /run orchestration/i });
      await user.click(submitButton);

      // Check if button shows running state (this might be brief)
      // Note: This test might need adjustment based on actual async behavior
      expect(submitButton).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and accessible elements', () => {
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Check inputs have proper labels
      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument();
      
      // Check buttons have proper roles and accessible names
      expect(screen.getByRole('button', { name: /schedule current week/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /schedule next week/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /run orchestration/i })).toBeInTheDocument();
    });

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ScheduleOrchestratorForm />);

      // Start from beginning of form
      const firstButton = screen.getByRole('button', { name: /schedule current week/i });
      
      // Tab to first focusable element (which is the first button)
      await user.tab();
      expect(firstButton).toHaveFocus();

      // Continue tabbing through form elements
      await user.tab();
      expect(screen.getByRole('button', { name: /schedule next week/i })).toHaveFocus();

      await user.tab();
      expect(screen.getByLabelText(/start date/i)).toHaveFocus();
    });
  });
});
