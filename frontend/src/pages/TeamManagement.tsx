import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Alert,
  CircularProgress,
  Tooltip,
  Stack,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
} from '@mui/material';
import {
  Edit,
  Delete,
  GroupAdd,
  PersonAdd,
  Remove,
  Visibility,
  People,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { formatDate } from '../utils/dateUtils';
import { apiClient } from '../services/apiClient';
import { API_CONFIG, buildEndpointUrl } from '../config/api';

interface User {
  id: number;
  username: string;
  email: string;
  name: string;
  is_active: boolean;
}

interface TeamMember {
  id: number;
  user: User;
  role: string;
  joined_date: string;
  is_active: boolean;
}

interface Team {
  id: number;
  name: string;
  description: string;
  department: string;
  manager: User | null;
  members: TeamMember[];
  created: string;
}

interface Department {
  id: number;
  name: string;
  description: string;
  manager: User | null;
}

const TeamManagement: React.FC = () => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [teamDialogOpen, setTeamDialogOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [memberDialogOpen, setMemberDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    department: '',
    manager: '',
  });
  
  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load teams
      const teamsData = await apiClient.get(API_CONFIG.ENDPOINTS.TEAMS_LIST) as any;
      setTeams(teamsData.results || teamsData);

      // Load departments
      const deptData = await apiClient.get(API_CONFIG.ENDPOINTS.DEPARTMENTS_LIST) as any;
      setDepartments(deptData.results || deptData);

      // Load users
      const usersData = await apiClient.get(API_CONFIG.ENDPOINTS.USERS_LIST) as any;
      setUsers(usersData.results || usersData);
    } catch (err) {
      setError('Failed to load data');
      console.error('Data loading error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateTeam = () => {
    setSelectedTeam(null);
    setFormData({
      name: '',
      description: '',
      department: '',
      manager: '',
    });
    setTeamDialogOpen(true);
  };

  const handleEditTeam = (team: Team) => {
    setSelectedTeam(team);
    setFormData({
      name: team.name,
      description: team.description,
      department: team.department,
      manager: team.manager?.id.toString() || '',
    });
    setTeamDialogOpen(true);
  };

  const handleSaveTeam = async () => {
    try {
      if (selectedTeam) {
        // Update existing team
        await apiClient.put(buildEndpointUrl(API_CONFIG.ENDPOINTS.TEAM_DETAIL, { id: selectedTeam.id }), formData);
      } else {
        // Create new team
        await apiClient.post(API_CONFIG.ENDPOINTS.TEAMS_LIST, formData);
      }
      
      setTeamDialogOpen(false);
      loadData(); // Reload data
    } catch (err) {
      setError('Failed to save team');
      console.error('Save team error:', err);
    }
  };

  const handleDeleteTeam = async (teamId: number) => {
    if (!confirm('Are you sure you want to delete this team?')) {
      return;
    }

    try {
      await apiClient.delete(buildEndpointUrl(API_CONFIG.ENDPOINTS.TEAM_DETAIL, { id: teamId }));
      loadData(); // Reload data
    } catch (err) {
      setError('Failed to delete team');
      console.error('Delete team error:', err);
    }
  };

  const handleAddMember = (team: Team) => {
    setSelectedTeam(team);
    setMemberDialogOpen(true);
  };

  const handleRemoveMember = async (teamId: number, memberId: number) => {
    if (!confirm('Are you sure you want to remove this member?')) {
      return;
    }

    try {
      await apiClient.delete(buildEndpointUrl(API_CONFIG.ENDPOINTS.TEAM_MEMBER, { teamId, memberId }));
      loadData(); // Reload data
    } catch (err) {
      setError('Failed to remove member');
      console.error('Remove member error:', err);
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'manager':
      case 'lead':
        return 'primary';
      case 'member':
        return 'default';
      default:
        return 'secondary';
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Team Management
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<People />}
            onClick={() => navigate('/user-management')}
          >
            User Management
          </Button>
          <Button
            variant="contained"
            startIcon={<GroupAdd />}
            onClick={handleCreateTeam}
          >
            Create Team
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Teams
              </Typography>
              <Typography variant="h4">
                {teams.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Departments
              </Typography>
              <Typography variant="h4" color="primary">
                {departments.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Members
              </Typography>
              <Typography variant="h4" color="success.main">
                {teams.reduce((sum, team) => sum + team.members.length, 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Teams Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Team</TableCell>
                <TableCell>Department</TableCell>
                <TableCell>Manager</TableCell>
                <TableCell>Members</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {teams.map((team) => (
                <TableRow key={team.id}>
                  <TableCell>
                    <Box>
                      <Typography variant="body1" fontWeight="bold">
                        {team.name}
                      </Typography>
                      {team.description && (
                        <Typography variant="body2" color="text.secondary">
                          {team.description}
                        </Typography>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip label={team.department} size="small" />
                  </TableCell>
                  <TableCell>
                    {team.manager ? (
                      <Box>
                        <Typography variant="body2">
                          {team.manager.name || team.manager.username}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {team.manager.email}
                        </Typography>
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No manager assigned
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {team.members.length} members
                      </Typography>
                      <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }}>
                        {team.members.slice(0, 3).map((member) => (
                          <Chip
                            key={member.id}
                            label={member.role}
                            size="small"
                            color={getRoleColor(member.role) as any}
                          />
                        ))}
                        {team.members.length > 3 && (
                          <Typography variant="caption" color="text.secondary">
                            +{team.members.length - 3} more
                          </Typography>
                        )}
                      </Stack>
                    </Box>
                  </TableCell>
                  <TableCell>
                    {formatDate(new Date(team.created))}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <Tooltip title="View Details">
                        <IconButton 
                          size="small" 
                          onClick={() => navigate(`/teams/${team.id}`)}
                        >
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Edit Team">
                        <IconButton size="small" onClick={() => handleEditTeam(team)}>
                          <Edit />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Add Member">
                        <IconButton 
                          size="small" 
                          color="primary"
                          onClick={() => handleAddMember(team)}
                        >
                          <PersonAdd />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Team">
                        <IconButton 
                          size="small" 
                          color="error"
                          onClick={() => handleDeleteTeam(team.id)}
                        >
                          <Delete />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Team Dialog */}
      <Dialog open={teamDialogOpen} onClose={() => setTeamDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {selectedTeam ? 'Edit Team' : 'Create New Team'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Team Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                multiline
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Department</InputLabel>
                <Select
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  label="Department"
                >
                  {departments.map((dept) => (
                    <MenuItem key={dept.id} value={dept.name}>
                      {dept.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Manager</InputLabel>
                <Select
                  value={formData.manager}
                  onChange={(e) => setFormData({ ...formData, manager: e.target.value })}
                  label="Manager"
                >
                  <MenuItem value="">No manager</MenuItem>
                  {users.filter(u => u.is_active).map((user) => (
                    <MenuItem key={user.id} value={user.id.toString()}>
                      {user.name || user.username} ({user.email})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTeamDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveTeam} variant="contained">
            {selectedTeam ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Member Dialog */}
      <Dialog open={memberDialogOpen} onClose={() => setMemberDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Team Members - {selectedTeam?.name}
        </DialogTitle>
        <DialogContent>
          <List>
            {selectedTeam?.members.map((member, index) => (
              <React.Fragment key={member.id}>
                <ListItem>
                  <ListItemText
                    primary={member.user.name || member.user.username}
                    secondary={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip 
                          label={member.role} 
                          size="small" 
                          color={getRoleColor(member.role) as any}
                        />
                        <Typography variant="caption">
                          Joined: {formatDate(new Date(member.joined_date))}
                        </Typography>
                      </Stack>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Tooltip title="Remove from team">
                      <IconButton 
                        size="small" 
                        color="error"
                        onClick={() => handleRemoveMember(selectedTeam.id, member.id)}
                      >
                        <Remove />
                      </IconButton>
                    </Tooltip>
                  </ListItemSecondaryAction>
                </ListItem>
                {index < selectedTeam.members.length - 1 && <Divider />}
              </React.Fragment>
            ))}
            {selectedTeam?.members.length === 0 && (
              <ListItem>
                <ListItemText 
                  primary="No members"
                  secondary="This team has no members yet"
                />
              </ListItem>
            )}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMemberDialogOpen(false)}>Close</Button>
          <Button variant="contained" startIcon={<PersonAdd />}>
            Add Member
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TeamManagement;
