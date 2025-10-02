import React from 'react';
import {
  Alert,
  AlertTitle,
  Box,
  Typography,
  Chip,
  List,
  ListItem,
  ListItemText,
  Collapse,
  IconButton,
  Button,
} from '@mui/material';
import {
  Warning as WarningIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CalendarToday as CalendarIcon,
  People as PeopleIcon,
  WorkOff as ShiftIcon,
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';
import type { ConflictCheckResponse } from '../../services/leaveConflictService';

interface ConflictWarningBannerProps {
  conflicts: ConflictCheckResponse;
  onViewAlternatives?: () => void;
}

const ConflictWarningBanner: React.FC<ConflictWarningBannerProps> = ({
  conflicts,
  onViewAlternatives,
}) => {
  const [expanded, setExpanded] = React.useState(false);

  if (!conflicts.has_conflicts) {
    return null;
  }

  const hasPersonalConflicts = conflicts.personal_conflicts.length > 0;
  const hasTeamConflicts = conflicts.team_conflicts_by_day.conflict_days.length > 0;
  const hasStaffingIssues =
    conflicts.staffing_analysis.understaffed_days.length > 0 ||
    conflicts.staffing_analysis.warning_days.length > 0;
  const hasShiftConflicts = conflicts.shift_conflicts.length > 0;

  // Determine severity
  const severity = hasPersonalConflicts || hasShiftConflicts ? 'error' : 'warning';

  return (
    <Alert
      severity={severity}
      icon={<WarningIcon />}
      sx={{ mb: 2 }}
      action={
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          {onViewAlternatives && (
            <Button
              size="small"
              color="inherit"
              variant="outlined"
              startIcon={<CalendarIcon />}
              onClick={onViewAlternatives}
            >
              View Alternatives
            </Button>
          )}
          <IconButton
            size="small"
            onClick={() => setExpanded(!expanded)}
            aria-label="show details"
          >
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      }
    >
      <AlertTitle>
        <strong>Leave Conflicts Detected</strong>
      </AlertTitle>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
        {hasPersonalConflicts && (
          <Chip
            size="small"
            icon={<CalendarIcon />}
            label={`${conflicts.personal_conflicts.length} Personal Conflict${
              conflicts.personal_conflicts.length > 1 ? 's' : ''
            }`}
            color="error"
          />
        )}
        {hasTeamConflicts && (
          <Chip
            size="small"
            icon={<PeopleIcon />}
            label={`${conflicts.team_conflicts_by_day.conflict_days.length} Day${
              conflicts.team_conflicts_by_day.conflict_days.length > 1 ? 's' : ''
            } with Team Conflicts`}
            color="warning"
          />
        )}
        {hasStaffingIssues && (
          <Chip
            size="small"
            icon={<WarningIcon />}
            label={`${conflicts.staffing_analysis.understaffed_days.length} Understaffed Day${
              conflicts.staffing_analysis.understaffed_days.length > 1 ? 's' : ''
            }`}
            color="warning"
          />
        )}
        {hasShiftConflicts && (
          <Chip
            size="small"
            icon={<ShiftIcon />}
            label={`${conflicts.shift_conflicts.length} Shift Conflict${
              conflicts.shift_conflicts.length > 1 ? 's' : ''
            }`}
            color="error"
          />
        )}
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ mt: 2 }}>
          {/* Personal Conflicts */}
          {hasPersonalConflicts && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Personal Leave Conflicts:
              </Typography>
              <List dense disablePadding>
                {conflicts.personal_conflicts.map((conflict, index) => (
                  <ListItem key={index} disableGutters>
                    <ListItemText
                      primary={`${format(parseISO(conflict.start_date), 'MMM d, yyyy')} - ${format(
                        parseISO(conflict.end_date),
                        'MMM d, yyyy'
                      )}`}
                      secondary={`${conflict.leave_type} (${conflict.status.toUpperCase()}) - ${
                        conflict.days_requested
                      } days`}
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {/* Team Conflicts */}
          {hasTeamConflicts && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Team Conflicts:
              </Typography>
              <List dense disablePadding>
                {conflicts.team_conflicts_by_day.conflict_days.slice(0, 5).map((day, index) => (
                  <ListItem key={index} disableGutters>
                    <ListItemText
                      primary={format(parseISO(day.date), 'MMM d, yyyy')}
                      secondary={`${day.leave_count} team member${
                        day.leave_count > 1 ? 's' : ''
                      } on leave`}
                    />
                  </ListItem>
                ))}
                {conflicts.team_conflicts_by_day.conflict_days.length > 5 && (
                  <ListItem disableGutters>
                    <ListItemText
                      secondary={`... and ${
                        conflicts.team_conflicts_by_day.conflict_days.length - 5
                      } more days`}
                    />
                  </ListItem>
                )}
              </List>
            </Box>
          )}

          {/* Staffing Issues */}
          {hasStaffingIssues && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Staffing Concerns:
              </Typography>
              <List dense disablePadding>
                {conflicts.staffing_analysis.understaffed_days.slice(0, 3).map((day, index) => (
                  <ListItem key={index} disableGutters>
                    <ListItemText
                      primary={format(parseISO(day.date), 'MMM d, yyyy')}
                      secondary={`${day.available_staff} available / ${day.required_staff} required (${day.shortage} short)`}
                    />
                  </ListItem>
                ))}
                {conflicts.staffing_analysis.understaffed_days.length > 3 && (
                  <ListItem disableGutters>
                    <ListItemText
                      secondary={`... and ${
                        conflicts.staffing_analysis.understaffed_days.length - 3
                      } more understaffed days`}
                    />
                  </ListItem>
                )}
              </List>
            </Box>
          )}

          {/* Shift Conflicts */}
          {hasShiftConflicts && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Scheduled Shift Conflicts:
              </Typography>
              <List dense disablePadding>
                {conflicts.shift_conflicts.map((shift, index) => (
                  <ListItem key={index} disableGutters>
                    <ListItemText
                      primary={`${format(parseISO(shift.shift_date), 'MMM d, yyyy')} - ${
                        shift.shift_type
                      }`}
                      secondary={`${shift.start_time} - ${shift.end_time}`}
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {severity === 'error' && (
            <Typography variant="body2" sx={{ mt: 2, fontStyle: 'italic' }}>
              ⚠️ You cannot submit this leave request due to existing conflicts or shift
              assignments. Please select different dates.
            </Typography>
          )}
        </Box>
      </Collapse>
    </Alert>
  );
};

export default ConflictWarningBanner;
