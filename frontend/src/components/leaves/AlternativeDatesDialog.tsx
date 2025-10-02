import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  TrendingFlat as ArrowIcon,
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';
import type { AlternativeSuggestion } from '../../services/leaveConflictService';

interface AlternativeDatesDialogProps {
  open: boolean;
  onClose: () => void;
  suggestions: AlternativeSuggestion[];
  loading?: boolean;
  originalStartDate: string;
  onSelectDate: (startDate: string, endDate: string) => void;
}

const AlternativeDatesDialog: React.FC<AlternativeDatesDialogProps> = ({
  open,
  onClose,
  suggestions,
  loading = false,
  originalStartDate,
  onSelectDate,
}) => {
  const getConflictColor = (score: number) => {
    if (score === 0) return 'success';
    if (score < 0.3) return 'info';
    if (score < 0.6) return 'warning';
    return 'error';
  };

  const getConflictLabel = (score: number) => {
    if (score === 0) return 'No Conflicts';
    if (score < 0.3) return 'Low Conflict';
    if (score < 0.6) return 'Moderate Conflict';
    return 'High Conflict';
  };

  const handleSelectDate = (suggestion: AlternativeSuggestion) => {
    onSelectDate(suggestion.start_date, suggestion.end_date);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CheckIcon color="primary" />
          <Typography variant="h6">Alternative Date Suggestions</Typography>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : suggestions.length === 0 ? (
          <Alert severity="info">
            No alternative dates found within the search window. Try selecting different dates or
            contact your manager.
          </Alert>
        ) : (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Based on team availability and staffing requirements, here are the best alternative
              dates for your leave:
            </Typography>

            <Grid container spacing={2}>
              {suggestions.map((suggestion, index) => (
                <Grid item xs={12} key={index}>
                  <Card
                    variant="outlined"
                    sx={{
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      '&:hover': {
                        boxShadow: 3,
                        borderColor: 'primary.main',
                      },
                    }}
                    onClick={() => handleSelectDate(suggestion)}
                  >
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                        <Box>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {format(parseISO(suggestion.start_date), 'MMM d, yyyy')} -{' '}
                            {format(parseISO(suggestion.end_date), 'MMM d, yyyy')}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {Math.ceil(
                              (parseISO(suggestion.end_date).getTime() -
                                parseISO(suggestion.start_date).getTime()) /
                                (1000 * 60 * 60 * 24)
                            ) + 1}{' '}
                            days
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                          <Chip
                            size="small"
                            label={getConflictLabel(suggestion.conflict_score)}
                            color={getConflictColor(suggestion.conflict_score)}
                            icon={
                              suggestion.conflict_score === 0 ? <CheckIcon /> : <WarningIcon />
                            }
                          />
                          {suggestion.is_understaffed && (
                            <Chip
                              size="small"
                              label="Understaffed"
                              color="warning"
                              variant="outlined"
                            />
                          )}
                        </Box>
                      </Box>

                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                          Original:{' '}
                          {format(parseISO(originalStartDate), 'MMM d, yyyy')}
                        </Typography>
                        <ArrowIcon fontSize="small" color="action" />
                        <Typography variant="body2" color="primary">
                          {suggestion.days_offset > 0 ? '+' : ''}
                          {suggestion.days_offset} days
                        </Typography>
                      </Box>

                      {index === 0 && (
                        <Box sx={{ mt: 2 }}>
                          <Chip
                            size="small"
                            label="Recommended"
                            color="primary"
                            variant="outlined"
                          />
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            <Box sx={{ mt: 3 }}>
              <Typography variant="caption" color="text.secondary">
                💡 Tip: Dates with "No Conflicts" are ideal for approval. Click any date to use
                it for your leave request.
              </Typography>
            </Box>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default AlternativeDatesDialog;
