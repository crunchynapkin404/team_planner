/**
 * Bulk Shift Operations Page
 * 
 * Provides UI for:
 * - Bulk creating shifts from templates
 * - Bulk assigning employees
 * - Bulk modifying shift times
 * - Bulk deleting shifts
 * - CSV import/export
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  TextField,
  Button,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  CircularProgress,
  FormControlLabel,
  Checkbox,
  Card,
  CardContent,
} from '@mui/material';
import {
  Add as AddIcon,
  PersonAdd as PersonAddIcon,
  AccessTime as TimeIcon,
  Delete as DeleteIcon,
  FileDownload as DownloadIcon,
  FileUpload as UploadIcon,
  Preview as PreviewIcon,
} from '@mui/icons-material';

import bulkShiftService, {
  BulkCreateRequest,
  BulkCreateResult,
  BulkAssignResult,
  BulkModifyTimesResult,
  BulkDeleteResult,
  ImportResult,
} from '../services/bulkShiftService';
import templateService, { ShiftTemplate } from '../services/templateService';
import { apiClient } from '../services/apiClient';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`bulk-tabpanel-${index}`}
      aria-labelledby={`bulk-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

// Employee interface (simplified)
interface Employee {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
}



const BulkShiftOperations: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Data state
  const [templates, setTemplates] = useState<ShiftTemplate[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  
  // Bulk Create state
  const [createForm, setCreateForm] = useState<BulkCreateRequest>({
    template_id: 0,
    start_date: '',
    end_date: '',
    employee_ids: [],
    start_time: '',
    end_time: '',
    rotation_strategy: 'sequential',
    dry_run: false,
  });
  const [createResult, setCreateResult] = useState<BulkCreateResult | null>(null);
  
  // Bulk Assign state
  const [assignShiftIds, setAssignShiftIds] = useState<string>('');
  const [assignEmployeeId, setAssignEmployeeId] = useState<number>(0);
  const [assignDryRun, setAssignDryRun] = useState(true);
  const [assignResult, setAssignResult] = useState<BulkAssignResult | null>(null);
  
  // Bulk Modify Times state
  const [modifyShiftIds, setModifyShiftIds] = useState<string>('');
  const [modifyStartTime, setModifyStartTime] = useState<string>('');
  const [modifyEndTime, setModifyEndTime] = useState<string>('');
  const [modifyOffset, setModifyOffset] = useState<string>('');
  const [modifyDryRun, setModifyDryRun] = useState(true);
  const [modifyResult, setModifyResult] = useState<BulkModifyTimesResult | null>(null);
  
  // Bulk Delete state
  const [deleteShiftIds, setDeleteShiftIds] = useState<string>('');
  const [deleteForce, setDeleteForce] = useState(false);
  const [deleteDryRun, setDeleteDryRun] = useState(true);
  const [deleteResult, setDeleteResult] = useState<BulkDeleteResult | null>(null);
  
  // CSV state
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvDryRun, setCsvDryRun] = useState(true);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [exportShiftIds, setExportShiftIds] = useState<string>('');
  
  // Load data
  useEffect(() => {
    loadTemplates();
    loadEmployees();
    loadShifts();
  }, []);
  
  const loadTemplates = async () => {
    try {
      const data = await templateService.listTemplates({ is_active: true });
      setTemplates(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };
  
  const loadEmployees = async () => {
    try {
      const response = await apiClient.get<Employee[]>('/api/users/');
      setEmployees(Array.isArray(response) ? response : []);
    } catch (err) {
      console.error('Failed to load employees:', err);
    }
  };
  
  const loadShifts = async () => {
    try {
      // Shifts will be loaded on-demand when needed
      // Could be extended to show recent shifts for reference
    } catch (err) {
      console.error('Failed to load shifts:', err);
    }
  };
  
  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setError(null);
    setSuccess(null);
  };
  
  // Bulk Create handlers
  const handleBulkCreate = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    setCreateResult(null);
    
    try {
      const result = await bulkShiftService.bulkCreateShifts(createForm);
      setCreateResult(result);
      
      if (createForm.dry_run) {
        setSuccess(`Preview: ${result.shifts_to_create} shifts would be created, ${result.conflicts} conflicts found`);
      } else {
        setSuccess(`Successfully created ${result.created} shifts!`);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to create shifts');
    } finally {
      setLoading(false);
    }
  };
  
  // Bulk Assign handlers
  const handleBulkAssign = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    setAssignResult(null);
    
    try {
      const shiftIds = assignShiftIds.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));
      
      if (shiftIds.length === 0) {
        setError('Please enter valid shift IDs');
        return;
      }
      
      const result = await bulkShiftService.bulkAssignEmployees({
        shift_ids: shiftIds,
        employee_id: assignEmployeeId,
        dry_run: assignDryRun,
      });
      setAssignResult(result);
      
      if (assignDryRun) {
        setSuccess(`Preview: ${result.shifts_to_update} shifts would be updated, ${result.conflicts} conflicts found`);
      } else {
        setSuccess(`Successfully updated ${result.updated} shifts!`);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to assign employees');
    } finally {
      setLoading(false);
    }
  };
  
  // Bulk Modify Times handlers
  const handleBulkModifyTimes = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    setModifyResult(null);
    
    try {
      const shiftIds = modifyShiftIds.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));
      
      if (shiftIds.length === 0) {
        setError('Please enter valid shift IDs');
        return;
      }
      
      const result = await bulkShiftService.bulkModifyTimes({
        shift_ids: shiftIds,
        new_start_time: modifyStartTime || undefined,
        new_end_time: modifyEndTime || undefined,
        time_offset_minutes: modifyOffset ? parseInt(modifyOffset) : undefined,
        dry_run: modifyDryRun,
      });
      setModifyResult(result);
      
      if (modifyDryRun) {
        setSuccess(`Preview: ${result.shifts_to_update} shifts would be updated, ${result.conflicts} conflicts found`);
      } else {
        setSuccess(`Successfully updated ${result.updated} shifts!`);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to modify times');
    } finally {
      setLoading(false);
    }
  };
  
  // Bulk Delete handlers
  const handleBulkDelete = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    setDeleteResult(null);
    
    try {
      const shiftIds = deleteShiftIds.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));
      
      if (shiftIds.length === 0) {
        setError('Please enter valid shift IDs');
        return;
      }
      
      const result = await bulkShiftService.bulkDeleteShifts({
        shift_ids: shiftIds,
        force: deleteForce,
        dry_run: deleteDryRun,
      });
      setDeleteResult(result);
      
      if (deleteDryRun) {
        setSuccess(`Preview: ${result.shifts_to_delete} shifts would be deleted, ${result.warnings} warnings found`);
      } else {
        setSuccess(`Successfully deleted ${result.deleted} shifts!`);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to delete shifts');
    } finally {
      setLoading(false);
    }
  };
  
  // CSV handlers
  const handleExportCSV = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const shiftIds = exportShiftIds.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));
      
      if (shiftIds.length === 0) {
        setError('Please enter valid shift IDs');
        return;
      }
      
      const blob = await bulkShiftService.exportShiftsCSV(shiftIds);
      bulkShiftService.downloadCSV(blob, `shifts_export_${new Date().toISOString().split('T')[0]}.csv`);
      setSuccess(`Exported ${shiftIds.length} shifts to CSV`);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to export CSV');
    } finally {
      setLoading(false);
    }
  };
  
  const handleImportCSV = async () => {
    if (!csvFile) {
      setError('Please select a CSV file');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    setImportResult(null);
    
    try {
      const result = await bulkShiftService.importShiftsCSVFile(csvFile, csvDryRun);
      setImportResult(result);
      
      if (csvDryRun) {
        setSuccess(`Preview: ${result.valid_shifts} valid shifts found, ${result.errors} errors found`);
      } else {
        setSuccess(`Successfully imported ${result.created} shifts!`);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to import CSV');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Bulk Shift Operations
      </Typography>
      
      <Paper>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="bulk operations tabs">
          <Tab label="Bulk Create" icon={<AddIcon />} />
          <Tab label="Bulk Assign" icon={<PersonAddIcon />} />
          <Tab label="Modify Times" icon={<TimeIcon />} />
          <Tab label="Bulk Delete" icon={<DeleteIcon />} />
          <Tab label="CSV Import/Export" icon={<UploadIcon />} />
        </Tabs>
        
        {error && (
          <Alert severity="error" sx={{ m: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        
        {success && (
          <Alert severity="success" sx={{ m: 2 }} onClose={() => setSuccess(null)}>
            {success}
          </Alert>
        )}
        
        {/* Bulk Create Tab */}
        <TabPanel value={tabValue} index={0}>
          <Typography variant="h6" gutterBottom>
            Create Multiple Shifts from Template
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Template</InputLabel>
                <Select
                  value={createForm.template_id}
                  onChange={(e) => setCreateForm({ ...createForm, template_id: Number(e.target.value) })}
                >
                  <MenuItem value={0}>Select a template...</MenuItem>
                  {templates.map((template) => (
                    <MenuItem key={template.id} value={template.id}>
                      {template.name} ({template.shift_type})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Rotation Strategy</InputLabel>
                <Select
                  value={createForm.rotation_strategy}
                  onChange={(e) => setCreateForm({ ...createForm, rotation_strategy: e.target.value as 'sequential' | 'distribute' })}
                >
                  <MenuItem value="sequential">Sequential (rotate through employees)</MenuItem>
                  <MenuItem value="distribute">Distribute (even distribution)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Start Date"
                type="date"
                value={createForm.start_date}
                onChange={(e) => setCreateForm({ ...createForm, start_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="End Date"
                type="date"
                value={createForm.end_date}
                onChange={(e) => setCreateForm({ ...createForm, end_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Start Time (optional)"
                type="time"
                value={createForm.start_time}
                onChange={(e) => setCreateForm({ ...createForm, start_time: e.target.value })}
                InputLabelProps={{ shrink: true }}
                helperText="Leave empty to use template default"
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="End Time (optional)"
                type="time"
                value={createForm.end_time}
                onChange={(e) => setCreateForm({ ...createForm, end_time: e.target.value })}
                InputLabelProps={{ shrink: true }}
                helperText="Leave empty to use template default"
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Employees</InputLabel>
                <Select
                  multiple
                  value={createForm.employee_ids}
                  onChange={(e) => setCreateForm({ ...createForm, employee_ids: e.target.value as number[] })}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => {
                        const emp = employees.find(e => e.id === value);
                        return emp ? <Chip key={value} label={emp.username} size="small" /> : null;
                      })}
                    </Box>
                  )}
                >
                  {employees.map((employee) => (
                    <MenuItem key={employee.id} value={employee.id}>
                      {employee.username} ({employee.email})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={createForm.dry_run}
                    onChange={(e) => setCreateForm({ ...createForm, dry_run: e.target.checked })}
                  />
                }
                label="Dry Run (preview only, don't create)"
              />
            </Grid>
            
            <Grid item xs={12}>
              <Button
                variant="contained"
                startIcon={loading ? <CircularProgress size={20} /> : <PreviewIcon />}
                onClick={handleBulkCreate}
                disabled={loading || !createForm.template_id || !createForm.start_date || !createForm.end_date || createForm.employee_ids.length === 0}
              >
                {createForm.dry_run ? 'Preview' : 'Create Shifts'}
              </Button>
            </Grid>
            
            {createResult && (
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Result</Typography>
                    <Typography>Template: {createResult.template_name}</Typography>
                    <Typography>Date Range: {createResult.date_range}</Typography>
                    <Typography>Total Days: {createResult.total_days}</Typography>
                    <Typography color="success.main">Shifts to Create: {createResult.shifts_to_create}</Typography>
                    <Typography color="error.main">Conflicts: {createResult.conflicts}</Typography>
                    {createResult.created > 0 && (
                      <Typography color="primary.main">Created: {createResult.created}</Typography>
                    )}
                    
                    {createResult.conflict_details && createResult.conflict_details.length > 0 && (
                      <>
                        <Typography variant="subtitle2" sx={{ mt: 2 }}>Conflict Details:</Typography>
                        {createResult.conflict_details.map((conflict, index) => (
                          <Alert key={index} severity="warning" sx={{ mt: 1 }}>
                            {conflict.date} - {conflict.employee}: {conflict.reason}
                          </Alert>
                        ))}
                      </>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        </TabPanel>
        
        {/* Bulk Assign Tab */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            Assign Employee to Multiple Shifts
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Shift IDs (comma-separated)"
                value={assignShiftIds}
                onChange={(e) => setAssignShiftIds(e.target.value)}
                placeholder="1, 2, 3, 4"
                helperText="Enter shift IDs separated by commas"
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Employee</InputLabel>
                <Select
                  value={assignEmployeeId}
                  onChange={(e) => setAssignEmployeeId(Number(e.target.value))}
                >
                  <MenuItem value={0}>Select an employee...</MenuItem>
                  {employees.map((employee) => (
                    <MenuItem key={employee.id} value={employee.id}>
                      {employee.username} ({employee.email})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={assignDryRun}
                    onChange={(e) => setAssignDryRun(e.target.checked)}
                  />
                }
                label="Dry Run (preview only)"
              />
            </Grid>
            
            <Grid item xs={12}>
              <Button
                variant="contained"
                startIcon={loading ? <CircularProgress size={20} /> : <PersonAddIcon />}
                onClick={handleBulkAssign}
                disabled={loading || !assignShiftIds || !assignEmployeeId}
              >
                {assignDryRun ? 'Preview' : 'Assign Employee'}
              </Button>
            </Grid>
            
            {assignResult && (
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Result</Typography>
                    <Typography>Employee: {assignResult.employee}</Typography>
                    <Typography>Total Shifts: {assignResult.total_shifts}</Typography>
                    <Typography color="success.main">Shifts to Update: {assignResult.shifts_to_update}</Typography>
                    <Typography color="error.main">Conflicts: {assignResult.conflicts}</Typography>
                    {assignResult.updated > 0 && (
                      <Typography color="primary.main">Updated: {assignResult.updated}</Typography>
                    )}
                    
                    {assignResult.conflict_details && assignResult.conflict_details.length > 0 && (
                      <>
                        <Typography variant="subtitle2" sx={{ mt: 2 }}>Conflict Details:</Typography>
                        {assignResult.conflict_details.map((conflict, index) => (
                          <Alert key={index} severity="warning" sx={{ mt: 1 }}>
                            Shift {conflict.shift_id} on {conflict.date} at {conflict.time}: {conflict.reason}
                          </Alert>
                        ))}
                      </>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        </TabPanel>
        
        {/* Bulk Modify Times Tab */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            Modify Times for Multiple Shifts
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Shift IDs (comma-separated)"
                value={modifyShiftIds}
                onChange={(e) => setModifyShiftIds(e.target.value)}
                placeholder="1, 2, 3, 4"
                helperText="Enter shift IDs separated by commas"
              />
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle2" gutterBottom>
                Option 1: Set New Times
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="New Start Time"
                type="time"
                value={modifyStartTime}
                onChange={(e) => setModifyStartTime(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="New End Time"
                type="time"
                value={modifyEndTime}
                onChange={(e) => setModifyEndTime(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle2" gutterBottom>
                Option 2: Offset Current Times
              </Typography>
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Time Offset (minutes)"
                type="number"
                value={modifyOffset}
                onChange={(e) => setModifyOffset(e.target.value)}
                helperText="Positive to shift later, negative to shift earlier"
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={modifyDryRun}
                    onChange={(e) => setModifyDryRun(e.target.checked)}
                  />
                }
                label="Dry Run (preview only)"
              />
            </Grid>
            
            <Grid item xs={12}>
              <Button
                variant="contained"
                startIcon={loading ? <CircularProgress size={20} /> : <TimeIcon />}
                onClick={handleBulkModifyTimes}
                disabled={loading || !modifyShiftIds || (!modifyStartTime && !modifyEndTime && !modifyOffset)}
              >
                {modifyDryRun ? 'Preview' : 'Modify Times'}
              </Button>
            </Grid>
            
            {modifyResult && (
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Result</Typography>
                    <Typography>Total Shifts: {modifyResult.total_shifts}</Typography>
                    <Typography color="success.main">Shifts to Update: {modifyResult.shifts_to_update}</Typography>
                    <Typography color="error.main">Conflicts: {modifyResult.conflicts}</Typography>
                    {modifyResult.updated > 0 && (
                      <Typography color="primary.main">Updated: {modifyResult.updated}</Typography>
                    )}
                    
                    {modifyResult.conflict_details && modifyResult.conflict_details.length > 0 && (
                      <>
                        <Typography variant="subtitle2" sx={{ mt: 2 }}>Conflict Details:</Typography>
                        {modifyResult.conflict_details.map((conflict, index) => (
                          <Alert key={index} severity="warning" sx={{ mt: 1 }}>
                            Shift {conflict.shift_id} - {conflict.employee}: {conflict.old_time} → {conflict.new_time} ({conflict.reason})
                          </Alert>
                        ))}
                      </>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        </TabPanel>
        
        {/* Bulk Delete Tab */}
        <TabPanel value={tabValue} index={3}>
          <Typography variant="h6" gutterBottom>
            Delete Multiple Shifts
          </Typography>
          
          <Alert severity="warning" sx={{ mb: 2 }}>
            This action cannot be undone. Use dry run to preview first.
          </Alert>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Shift IDs (comma-separated)"
                value={deleteShiftIds}
                onChange={(e) => setDeleteShiftIds(e.target.value)}
                placeholder="1, 2, 3, 4"
                helperText="Enter shift IDs separated by commas"
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={deleteForce}
                    onChange={(e) => setDeleteForce(e.target.checked)}
                  />
                }
                label="Force Delete (skip validation for in-progress/completed shifts)"
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={deleteDryRun}
                    onChange={(e) => setDeleteDryRun(e.target.checked)}
                  />
                }
                label="Dry Run (preview only)"
              />
            </Grid>
            
            <Grid item xs={12}>
              <Button
                variant="contained"
                color="error"
                startIcon={loading ? <CircularProgress size={20} /> : <DeleteIcon />}
                onClick={handleBulkDelete}
                disabled={loading || !deleteShiftIds}
              >
                {deleteDryRun ? 'Preview' : 'Delete Shifts'}
              </Button>
            </Grid>
            
            {deleteResult && (
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Result</Typography>
                    <Typography>Total Shifts: {deleteResult.total_shifts}</Typography>
                    <Typography color="success.main">Shifts to Delete: {deleteResult.shifts_to_delete}</Typography>
                    <Typography color="warning.main">Warnings: {deleteResult.warnings}</Typography>
                    {deleteResult.deleted > 0 && (
                      <Typography color="error.main">Deleted: {deleteResult.deleted}</Typography>
                    )}
                    
                    {deleteResult.warning_details && deleteResult.warning_details.length > 0 && (
                      <>
                        <Typography variant="subtitle2" sx={{ mt: 2 }}>Warnings:</Typography>
                        {deleteResult.warning_details.map((warning, index) => (
                          <Alert key={index} severity="warning" sx={{ mt: 1 }}>
                            Shift {warning.shift_id} - {warning.employee} on {warning.date}: {warning.reason} (Status: {warning.status})
                          </Alert>
                        ))}
                      </>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        </TabPanel>
        
        {/* CSV Import/Export Tab */}
        <TabPanel value={tabValue} index={4}>
          <Typography variant="h6" gutterBottom>
            CSV Import/Export
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>Export Shifts</Typography>
              <TextField
                fullWidth
                label="Shift IDs to Export (comma-separated)"
                value={exportShiftIds}
                onChange={(e) => setExportShiftIds(e.target.value)}
                placeholder="1, 2, 3, 4"
                sx={{ mb: 2 }}
              />
              <Button
                variant="contained"
                startIcon={loading ? <CircularProgress size={20} /> : <DownloadIcon />}
                onClick={handleExportCSV}
                disabled={loading || !exportShiftIds}
              >
                Export to CSV
              </Button>
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>Import Shifts</Typography>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                style={{ marginBottom: '16px' }}
              />
              
              <FormControlLabel
                control={
                  <Checkbox
                    checked={csvDryRun}
                    onChange={(e) => setCsvDryRun(e.target.checked)}
                  />
                }
                label="Dry Run (preview only)"
                sx={{ display: 'block', mb: 2 }}
              />
              
              <Button
                variant="contained"
                startIcon={loading ? <CircularProgress size={20} /> : <UploadIcon />}
                onClick={handleImportCSV}
                disabled={loading || !csvFile}
              >
                {csvDryRun ? 'Preview Import' : 'Import CSV'}
              </Button>
            </Grid>
            
            {importResult && (
              <Grid item xs={12}>
                <Card sx={{ mt: 2 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Import Result</Typography>
                    <Typography>Total Rows: {importResult.total_rows}</Typography>
                    <Typography color="success.main">Valid Shifts: {importResult.valid_shifts}</Typography>
                    <Typography color="error.main">Errors: {importResult.errors}</Typography>
                    {importResult.created > 0 && (
                      <Typography color="primary.main">Created: {importResult.created}</Typography>
                    )}
                    
                    {importResult.error_details && importResult.error_details.length > 0 && (
                      <>
                        <Typography variant="subtitle2" sx={{ mt: 2 }}>Error Details:</Typography>
                        {importResult.error_details.map((error, index) => (
                          <Alert key={index} severity="error" sx={{ mt: 1 }}>
                            Row {error.row}: {error.error}
                          </Alert>
                        ))}
                      </>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )}
            
            <Grid item xs={12}>
              <Alert severity="info" sx={{ mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>CSV Format:</Typography>
                <Typography variant="body2">
                  Template Name, Employee Username, Start Date, Start Time, End Date, End Time, Status, Notes
                </Typography>
                <Typography variant="body2">
                  Example: "Night Shift", "john_doe", "2025-01-01", "22:00:00", "2025-01-02", "06:00:00", "Scheduled", "Regular shift"
                </Typography>
              </Alert>
            </Grid>
          </Grid>
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default BulkShiftOperations;
