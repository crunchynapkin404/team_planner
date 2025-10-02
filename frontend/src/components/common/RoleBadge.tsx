import React from 'react';
import { Chip, ChipProps, Tooltip } from '@mui/material';
import {
  AdminPanelSettings,
  ManageAccounts,
  CalendarMonth,
  GroupWork,
  Person,
} from '@mui/icons-material';

interface RoleBadgeProps {
  role: string;
  size?: ChipProps['size'];
  showIcon?: boolean;
  showTooltip?: boolean;
}

const roleConfig: Record<string, {
  label: string;
  color: ChipProps['color'];
  icon: React.ReactElement;
  description: string;
}> = {
  admin: {
    label: 'Admin',
    color: 'error',
    icon: <AdminPanelSettings />,
    description: 'Full system access with all permissions',
  },
  manager: {
    label: 'Manager',
    color: 'warning',
    icon: <ManageAccounts />,
    description: 'Can manage teams, approve requests, and run orchestrator',
  },
  scheduler: {
    label: 'Scheduler',
    color: 'info',
    icon: <CalendarMonth />,
    description: 'Can create and edit shifts, manage schedules',
  },
  team_lead: {
    label: 'Team Lead',
    color: 'primary',
    icon: <GroupWork />,
    description: 'Can manage their team and view team schedules',
  },
  employee: {
    label: 'Employee',
    color: 'default',
    icon: <Person />,
    description: 'Basic access to view own schedules and request swaps',
  },
};

export const RoleBadge: React.FC<RoleBadgeProps> = ({
  role,
  size = 'small',
  showIcon = true,
  showTooltip = true,
}) => {
  const normalizedRole = role.toLowerCase();
  const config = roleConfig[normalizedRole] || {
    label: role,
    color: 'default' as ChipProps['color'],
    icon: <Person />,
    description: `Role: ${role}`,
  };

  const chip = (
    <Chip
      label={config.label}
      color={config.color}
      size={size}
      icon={showIcon ? config.icon : undefined}
      sx={{ fontWeight: 500 }}
    />
  );

  if (showTooltip) {
    return (
      <Tooltip title={config.description} arrow>
        {chip}
      </Tooltip>
    );
  }

  return chip;
};

export default RoleBadge;
