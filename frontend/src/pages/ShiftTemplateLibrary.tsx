/**
 * Shift Template Library Page
 * 
 * Browse, search, create, and manage shift templates.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  Alert,
  Tooltip,
  InputAdornment,
  Stack,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ContentCopy as CloneIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Search as SearchIcon,
  AccessTime as TimeIcon,
  Category as CategoryIcon,
} from '@mui/icons-material';
import templateService, {
  ShiftTemplate,
  ShiftTemplateCreate,
} from '../services/templateService';

const SHIFT_TYPES = [
  { value: 'incidents', label: 'Incidents' },
  { value: 'incidents_standby', label: 'Incidents-Standby' },
  { value: 'waakdienst', label: 'Waakdienst' },
  { value: 'changes', label: 'Changes' },
  { value: 'projects', label: 'Projects' },
];

const ShiftTemplateLibrary: React.FC = () => {
  const [templates, setTemplates] = useState<ShiftTemplate[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<ShiftTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [showActiveOnly, setShowActiveOnly] = useState(true);
  
  // Dialog states
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ShiftTemplate | null>(null);
  
  // Form state
  const [formData, setFormData] = useState<ShiftTemplateCreate>({
    name: '',
    shift_type: 'incidents',
    description: '',
    duration_hours: 8,
    category: '',
    tags: [],
    is_active: true,
    is_favorite: false,
    default_start_time: '09:00',
    default_end_time: '17:00',
    notes: '',
  });
  
  // Tag input
  const [tagInput, setTagInput] = useState('');

  useEffect(() => {
    loadTemplates();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [templates, searchQuery, filterType, filterCategory, showFavoritesOnly, showActiveOnly]);

  const loadTemplates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data: any = await templateService.listTemplates();
      const templatesArray = Array.isArray(data) ? data : (data?.results || []);
      setTemplates(templatesArray);
    } catch (err: any) {
      setError(err.message || 'Failed to load templates');
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...templates];
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(t => 
        t.name.toLowerCase().includes(query) ||
        t.description.toLowerCase().includes(query) ||
        t.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }
    
    if (filterType) {
      filtered = filtered.filter(t => t.shift_type === filterType);
    }
    
    if (filterCategory) {
      filtered = filtered.filter(t => t.category === filterCategory);
    }
    
    if (showFavoritesOnly) {
      filtered = filtered.filter(t => t.is_favorite);
    }
    
    if (showActiveOnly) {
      filtered = filtered.filter(t => t.is_active);
    }
    
    setFilteredTemplates(filtered);
  };

  const handleCreate = () => {
    setFormData({
      name: '',
      shift_type: 'incidents',
      description: '',
      duration_hours: 8,
      category: '',
      tags: [],
      is_active: true,
      is_favorite: false,
      default_start_time: '09:00',
      default_end_time: '17:00',
      notes: '',
    });
    setEditingTemplate(null);
    setDialogOpen(true);
  };

  const handleEdit = (template: ShiftTemplate) => {
    setFormData({
      name: template.name,
      shift_type: template.shift_type,
      description: template.description,
      duration_hours: template.duration_hours,
      category: template.category,
      tags: template.tags,
      is_active: template.is_active,
      is_favorite: template.is_favorite,
      default_start_time: template.default_start_time || '09:00',
      default_end_time: template.default_end_time || '17:00',
      notes: template.notes,
    });
    setEditingTemplate(template);
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setError(null);
    setSuccess(null);
    
    try {
      if (editingTemplate) {
        await templateService.updateTemplate(editingTemplate.id, formData);
        setSuccess('Template updated successfully');
      } else {
        await templateService.createTemplate(formData);
        setSuccess('Template created successfully');
      }
      setDialogOpen(false);
      loadTemplates();
    } catch (err: any) {
      setError(err.message || 'Failed to save template');
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;
    
    try {
      await templateService.deleteTemplate(id);
      setSuccess('Template deleted successfully');
      loadTemplates();
    } catch (err: any) {
      setError(err.message || 'Failed to delete template');
    }
  };

  const handleClone = async (id: number, name: string) => {
    try {
      await templateService.cloneTemplate(id);
      setSuccess(`"${name}" cloned successfully`);
      loadTemplates();
    } catch (err: any) {
      setError(err.message || 'Failed to clone template');
    }
  };

  const handleToggleFavorite = async (id: number) => {
    try {
      await templateService.toggleFavorite(id);
      loadTemplates();
    } catch (err: any) {
      setError(err.message || 'Failed to update favorite status');
    }
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags?.includes(tagInput.trim())) {
      setFormData({
        ...formData,
        tags: [...(formData.tags || []), tagInput.trim()],
      });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setFormData({
      ...formData,
      tags: formData.tags?.filter(t => t !== tag) || [],
    });
  };

  const getUniqueCategories = () => {
    const categories = new Set(templates.map(t => t.category).filter(Boolean));
    return Array.from(categories).sort();
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Shift Template Library</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreate}
        >
          Create Template
        </Button>
      </Box>

      {/* Alerts */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                placeholder="Search templates..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={2}>
              <FormControl fullWidth>
                <InputLabel>Type</InputLabel>
                <Select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  label="Type"
                >
                  <MenuItem value="">All Types</MenuItem>
                  {SHIFT_TYPES.map(type => (
                    <MenuItem key={type.value} value={type.value}>{type.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6} md={2}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                  label="Category"
                >
                  <MenuItem value="">All Categories</MenuItem>
                  {getUniqueCategories().map(cat => (
                    <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={6} sm={3} md={2}>
              <Button
                fullWidth
                variant={showFavoritesOnly ? 'contained' : 'outlined'}
                startIcon={<StarIcon />}
                onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
              >
                Favorites
              </Button>
            </Grid>
            
            <Grid item xs={6} sm={3} md={2}>
              <Button
                fullWidth
                variant={showActiveOnly ? 'contained' : 'outlined'}
                onClick={() => setShowActiveOnly(!showActiveOnly)}
              >
                Active Only
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Loading */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Template Grid */}
      {!loading && (
        <Grid container spacing={3}>
          {filteredTemplates.map((template) => (
            <Grid item xs={12} sm={6} md={4} key={template.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  {/* Header with favorite */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                      {template.name}
                    </Typography>
                    <IconButton
                      size="small"
                      onClick={() => handleToggleFavorite(template.id)}
                      color={template.is_favorite ? 'warning' : 'default'}
                    >
                      {template.is_favorite ? <StarIcon /> : <StarBorderIcon />}
                    </IconButton>
                  </Box>
                  
                  {/* Shift Type */}
                  <Chip
                    label={template.shift_type_display}
                    size="small"
                    color="primary"
                    sx={{ mb: 1 }}
                  />
                  
                  {/* Category */}
                  {template.category && (
                    <Chip
                      label={template.category}
                      size="small"
                      icon={<CategoryIcon />}
                      sx={{ mb: 1, ml: 1 }}
                    />
                  )}
                  
                  {/* Status */}
                  {!template.is_active && (
                    <Chip
                      label="Inactive"
                      size="small"
                      sx={{ mb: 1, ml: 1 }}
                    />
                  )}
                  
                  {/* Description */}
                  {template.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {template.description}
                    </Typography>
                  )}
                  
                  {/* Details */}
                  <Stack spacing={1}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <TimeIcon fontSize="small" color="action" />
                      <Typography variant="body2">
                        {template.duration_hours} hours
                      </Typography>
                    </Box>
                    
                    {(template.default_start_time && template.default_end_time) && (
                      <Typography variant="body2" color="text.secondary">
                        Default: {template.default_start_time} - {template.default_end_time}
                      </Typography>
                    )}
                    
                    {template.usage_count > 0 && (
                      <Typography variant="caption" color="text.secondary">
                        Used {template.usage_count} times
                      </Typography>
                    )}
                  </Stack>
                  
                  {/* Tags */}
                  {template.tags.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      {template.tags.map((tag, index) => (
                        <Chip
                          key={index}
                          label={tag}
                          size="small"
                          variant="outlined"
                          sx={{ mr: 0.5, mb: 0.5 }}
                        />
                      ))}
                    </Box>
                  )}
                </CardContent>
                
                <Divider />
                
                <CardActions>
                  <Tooltip title="Edit">
                    <IconButton size="small" onClick={() => handleEdit(template)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Clone">
                    <IconButton size="small" onClick={() => handleClone(template.id, template.name)}>
                      <CloneIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton size="small" onClick={() => handleDelete(template.id, template.name)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </CardActions>
              </Card>
            </Grid>
          ))}
          
          {filteredTemplates.length === 0 && (
            <Grid item xs={12}>
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography color="text.secondary">
                  {searchQuery || filterType || filterCategory || showFavoritesOnly
                    ? 'No templates match your filters'
                    : 'No templates found. Create one to get started!'}
                </Typography>
              </Box>
            </Grid>
          )}
        </Grid>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingTemplate ? 'Edit Template' : 'Create Template'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Template Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required>
                <InputLabel>Shift Type</InputLabel>
                <Select
                  value={formData.shift_type}
                  onChange={(e) => setFormData({ ...formData, shift_type: e.target.value })}
                  label="Shift Type"
                >
                  {SHIFT_TYPES.map(type => (
                    <MenuItem key={type.value} value={type.value}>{type.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Duration (hours)"
                type="number"
                value={formData.duration_hours}
                onChange={(e) => setFormData({ ...formData, duration_hours: Number(e.target.value) })}
                required
                inputProps={{ min: 1, max: 24 }}
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Category"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                placeholder="e.g., Weekend, Holiday, Standard"
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <Box>
                <TextField
                  fullWidth
                  label="Add Tag"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTag();
                    }
                  }}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <Button size="small" onClick={handleAddTag}>Add</Button>
                      </InputAdornment>
                    ),
                  }}
                />
                <Box sx={{ mt: 1 }}>
                  {formData.tags?.map((tag, index) => (
                    <Chip
                      key={index}
                      label={tag}
                      size="small"
                      onDelete={() => handleRemoveTag(tag)}
                      sx={{ mr: 0.5, mb: 0.5 }}
                    />
                  ))}
                </Box>
              </Box>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Default Start Time"
                type="time"
                value={formData.default_start_time}
                onChange={(e) => setFormData({ ...formData, default_start_time: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Default End Time"
                type="time"
                value={formData.default_end_time}
                onChange={(e) => setFormData({ ...formData, default_end_time: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                multiline
                rows={3}
                placeholder="Additional notes or instructions..."
              />
            </Grid>
            
            <Grid item xs={6}>
              <Button
                variant="outlined"
                startIcon={formData.is_active ? undefined : <StarIcon />}
                fullWidth
                onClick={() => setFormData({ ...formData, is_active: !formData.is_active })}
              >
                {formData.is_active ? 'Active' : 'Inactive'}
              </Button>
            </Grid>
            
            <Grid item xs={6}>
              <Button
                variant="outlined"
                startIcon={formData.is_favorite ? <StarIcon /> : <StarBorderIcon />}
                fullWidth
                onClick={() => setFormData({ ...formData, is_favorite: !formData.is_favorite })}
              >
                {formData.is_favorite ? 'Favorite' : 'Not Favorite'}
              </Button>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={!formData.name || !formData.shift_type || !formData.duration_hours}
          >
            {editingTemplate ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ShiftTemplateLibrary;
