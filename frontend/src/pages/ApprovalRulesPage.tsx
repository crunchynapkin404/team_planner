import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Switch,
  MenuItem,
  Alert,
  CircularProgress,
  Tooltip,
  Stack,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Rule as RuleIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  ArrowUpward,
  ArrowDownward,
} from '@mui/icons-material';
import swapApprovalService, {
  type ApprovalRule,
  type ApprovalRuleCreate,
} from '../services/swapApprovalService';

const ApprovalRulesPage: React.FC = () => {
  const [rules, setRules] = useState<ApprovalRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ApprovalRule | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [ruleToDelete, setRuleToDelete] = useState<ApprovalRule | null>(null);

  // Form state
  const [formData, setFormData] = useState<ApprovalRuleCreate>({
    name: '',
    description: '',
    priority: 100,
    is_active: true,
    applies_to_shift_types: [],
    requires_levels: 1,
    auto_approve_enabled: false,
    auto_approve_same_shift_type: false,
    auto_approve_max_advance_hours: null,
    auto_approve_min_seniority_months: null,
    auto_approve_skills_match_required: false,
    max_swaps_per_month_per_employee: null,
  });

  const shiftTypes = [
    'incident',
    'incidents',
    'incidents_standby',
    'waakdienst',
    'project',
    'change',
  ];

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await swapApprovalService.getApprovalRules();
      setRules(data);
    } catch (err) {
      setError('Failed to load approval rules');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (rule?: ApprovalRule) => {
    if (rule) {
      setEditingRule(rule);
      setFormData({
        name: rule.name,
        description: rule.description,
        priority: rule.priority,
        is_active: rule.is_active,
        applies_to_shift_types: rule.applies_to_shift_types,
        requires_levels: rule.requires_levels,
        auto_approve_enabled: rule.auto_approve_enabled,
        auto_approve_same_shift_type: rule.auto_approve_same_shift_type,
        auto_approve_max_advance_hours: rule.auto_approve_max_advance_hours,
        auto_approve_min_seniority_months: rule.auto_approve_min_seniority_months,
        auto_approve_skills_match_required: rule.auto_approve_skills_match_required,
        max_swaps_per_month_per_employee: rule.max_swaps_per_month_per_employee,
      });
    } else {
      setEditingRule(null);
      setFormData({
        name: '',
        description: '',
        priority: 100,
        is_active: true,
        applies_to_shift_types: [],
        requires_levels: 1,
        auto_approve_enabled: false,
        auto_approve_same_shift_type: false,
        auto_approve_max_advance_hours: null,
        auto_approve_min_seniority_months: null,
        auto_approve_skills_match_required: false,
        max_swaps_per_month_per_employee: null,
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingRule(null);
  };

  const handleSubmit = async () => {
    try {
      if (editingRule) {
        await swapApprovalService.updateApprovalRule(editingRule.id, formData);
      } else {
        await swapApprovalService.createApprovalRule(formData);
      }
      await fetchRules();
      handleCloseDialog();
    } catch (err) {
      setError(`Failed to ${editingRule ? 'update' : 'create'} approval rule`);
      console.error(err);
    }
  };

  const handleDelete = async () => {
    if (!ruleToDelete) return;
    
    try {
      await swapApprovalService.deleteApprovalRule(ruleToDelete.id);
      await fetchRules();
      setDeleteConfirmOpen(false);
      setRuleToDelete(null);
    } catch (err) {
      setError('Failed to delete approval rule');
      console.error(err);
    }
  };

  const handleOpenDeleteConfirm = (rule: ApprovalRule) => {
    setRuleToDelete(rule);
    setDeleteConfirmOpen(true);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            <RuleIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Approval Rules
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure automated approval workflows and rules for swap requests
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Create Rule
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Summary Cards */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="caption">
              Total Rules
            </Typography>
            <Typography variant="h4">{rules.length}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="caption">
              Active Rules
            </Typography>
            <Typography variant="h4">
              {rules.filter(r => r.is_active).length}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" variant="caption">
              Auto-Approve Enabled
            </Typography>
            <Typography variant="h4">
              {rules.filter(r => r.auto_approve_enabled).length}
            </Typography>
          </CardContent>
        </Card>
      </Stack>

      {/* Rules Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Priority</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Shift Types</TableCell>
              <TableCell>Approval Levels</TableCell>
              <TableCell>Auto-Approve</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rules.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 8 }}>
                  <Typography color="text.secondary">
                    No approval rules configured. Create your first rule to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              rules.map((rule) => (
                <TableRow key={rule.id} hover>
                  <TableCell>
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      {rule.priority >= 100 ? (
                        <ArrowUpward fontSize="small" color="error" />
                      ) : (
                        <ArrowDownward fontSize="small" color="action" />
                      )}
                      <Typography fontWeight="bold">{rule.priority}</Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Typography fontWeight="medium">{rule.name}</Typography>
                    {rule.description && (
                      <Typography variant="caption" color="text.secondary">
                        {rule.description}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {rule.applies_to_shift_types.length === 0 ? (
                      <Chip label="All Types" size="small" />
                    ) : (
                      <Stack direction="row" spacing={0.5} flexWrap="wrap">
                        {rule.applies_to_shift_types.map((type) => (
                          <Chip key={type} label={type} size="small" />
                        ))}
                      </Stack>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={`${rule.requires_levels} ${rule.requires_levels === 1 ? 'Level' : 'Levels'}`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    {rule.auto_approve_enabled ? (
                      <Chip
                        icon={<CheckCircleIcon />}
                        label="Enabled"
                        size="small"
                        color="success"
                      />
                    ) : (
                      <Chip
                        icon={<CancelIcon />}
                        label="Disabled"
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={rule.is_active ? 'Active' : 'Inactive'}
                      size="small"
                      color={rule.is_active ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Edit">
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(rule)}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleOpenDeleteConfirm(rule)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingRule ? 'Edit Approval Rule' : 'Create Approval Rule'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Basic Info */}
            <TextField
              label="Rule Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              fullWidth
            />

            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              multiline
              rows={2}
              fullWidth
            />

            <Stack direction="row" spacing={2}>
              <TextField
                label="Priority"
                type="number"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                helperText="Higher priority rules are evaluated first"
                fullWidth
              />

              <TextField
                label="Approval Levels Required"
                type="number"
                value={formData.requires_levels}
                onChange={(e) => setFormData({ ...formData, requires_levels: parseInt(e.target.value) })}
                inputProps={{ min: 1, max: 5 }}
                helperText="1-5 approval levels"
                fullWidth
              />
            </Stack>

            <TextField
              select
              label="Applies to Shift Types"
              value={formData.applies_to_shift_types}
              onChange={(e) => setFormData({ ...formData, applies_to_shift_types: e.target.value as any })}
              SelectProps={{ multiple: true }}
              helperText="Leave empty to apply to all shift types"
              fullWidth
            >
              {shiftTypes.map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </TextField>

            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
              }
              label="Rule is Active"
            />

            <Divider />

            {/* Auto-Approval Settings */}
            <Typography variant="subtitle1" fontWeight="bold">
              Auto-Approval Settings
            </Typography>

            <FormControlLabel
              control={
                <Switch
                  checked={formData.auto_approve_enabled}
                  onChange={(e) => setFormData({ ...formData, auto_approve_enabled: e.target.checked })}
                />
              }
              label="Enable Auto-Approval"
            />

            {formData.auto_approve_enabled && (
              <>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.auto_approve_same_shift_type}
                      onChange={(e) => setFormData({ ...formData, auto_approve_same_shift_type: e.target.checked })}
                    />
                  }
                  label="Require Same Shift Type"
                />

                <TextField
                  label="Max Advance Hours"
                  type="number"
                  value={formData.auto_approve_max_advance_hours || ''}
                  onChange={(e) => setFormData({
                    ...formData,
                    auto_approve_max_advance_hours: e.target.value ? parseInt(e.target.value) : null
                  })}
                  helperText="Maximum hours before shift for auto-approval"
                  fullWidth
                />

                <TextField
                  label="Minimum Seniority (Months)"
                  type="number"
                  value={formData.auto_approve_min_seniority_months || ''}
                  onChange={(e) => setFormData({
                    ...formData,
                    auto_approve_min_seniority_months: e.target.value ? parseInt(e.target.value) : null
                  })}
                  helperText="Minimum months of seniority required"
                  fullWidth
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.auto_approve_skills_match_required}
                      onChange={(e) => setFormData({ ...formData, auto_approve_skills_match_required: e.target.checked })}
                    />
                  }
                  label="Require Skills Match"
                />
              </>
            )}

            <Divider />

            {/* Limits */}
            <Typography variant="subtitle1" fontWeight="bold">
              Limits
            </Typography>

            <TextField
              label="Max Swaps Per Month Per Employee"
              type="number"
              value={formData.max_swaps_per_month_per_employee || ''}
              onChange={(e) => setFormData({
                ...formData,
                max_swaps_per_month_per_employee: e.target.value ? parseInt(e.target.value) : null
              })}
              helperText="Leave empty for unlimited"
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={!formData.name || formData.requires_levels < 1}
          >
            {editingRule ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onClose={() => setDeleteConfirmOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the rule "{ruleToDelete?.name}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmOpen(false)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ApprovalRulesPage;
