/**
 * Advanced Swap Approval Service
 * 
 * Provides API integration for:
 * - Approval rules management
 * - Swap approval workflows
 * - Approval delegations
 * - Audit trail viewing
 */

import { apiClient } from './apiClient';
import { API_CONFIG } from '../config/api';

// ============================================================================
// Type Definitions
// ============================================================================

export interface ApprovalRule {
  id: number;
  name: string;
  description: string;
  priority: number;
  is_active: boolean;
  applies_to_shift_types: string[];
  requires_levels: number;
  auto_approve_enabled: boolean;
  auto_approve_same_shift_type: boolean;
  auto_approve_max_advance_hours: number | null;
  auto_approve_min_seniority_months: number | null;
  auto_approve_skills_match_required: boolean;
  max_swaps_per_month_per_employee: number | null;
  created: string;
  updated: string;
}

export interface ApprovalRuleCreate {
  name: string;
  description?: string;
  priority: number;
  is_active?: boolean;
  applies_to_shift_types?: string[];
  requires_levels: number;
  auto_approve_enabled?: boolean;
  auto_approve_same_shift_type?: boolean;
  auto_approve_max_advance_hours?: number | null;
  auto_approve_min_seniority_months?: number | null;
  auto_approve_skills_match_required?: boolean;
  max_swaps_per_month_per_employee?: number | null;
}

export interface ApprovalChainStep {
  id: number;
  level: number;
  approver_id: number;
  approver_name: string;
  status: 'pending' | 'approved' | 'rejected';
  approved_at: string | null;
  rejected_at: string | null;
  comments: string | null;
}

export interface ApprovalChain {
  id: number;
  swap_request_id: number;
  rule_id: number;
  rule_name: string;
  current_level: number;
  total_levels: number;
  status: 'pending' | 'approved' | 'rejected' | 'auto_approved';
  steps: ApprovalChainStep[];
  can_auto_approve: boolean;
  auto_approve_reason: string;
  created: string;
  completed_at: string | null;
}

export interface PendingApproval {
  id: number;
  swap_request_id: number;
  requesting_employee: string;
  target_employee: string;
  requesting_shift_date: string;
  requesting_shift_time: string;
  target_shift_date: string | null;
  target_shift_time: string | null;
  shift_type: string;
  current_level: number;
  total_levels: number;
  requested_date: string;
  is_delegated: boolean;
  delegated_from: string | null;
}

export interface ApprovalDelegation {
  id: number;
  delegating_user_id: number;
  delegating_user_name: string;
  delegate_to_user_id: number;
  delegate_to_user_name: string;
  start_date: string;
  end_date: string;
  reason: string;
  is_active: boolean;
  created: string;
}

export interface ApprovalDelegationCreate {
  delegate_to_user_id: number;
  start_date: string;
  end_date: string;
  reason: string;
}

export interface AuditTrailEntry {
  id: number;
  swap_request_id: number;
  action: 'created' | 'approved' | 'rejected' | 'auto_approved' | 'delegated';
  level: number;
  performed_by_id: number;
  performed_by_name: string;
  comments: string | null;
  timestamp: string;
}

export interface ApproveSwapRequest {
  comments?: string;
}

export interface RejectSwapRequest {
  reason: string;
}

export interface ApprovalRulesResponse {
  count: number;
  results: ApprovalRule[];
}

export interface PendingApprovalsResponse {
  count: number;
  results: PendingApproval[];
}

export interface ApprovalDelegationsResponse {
  count: number;
  results: ApprovalDelegation[];
}

export interface AuditTrailResponse {
  count: number;
  results: AuditTrailEntry[];
}

// ============================================================================
// API Service
// ============================================================================

class SwapApprovalService {
  // --------------------------------------------------------------------------
  // Approval Rules Management
  // --------------------------------------------------------------------------

  /**
   * Get all approval rules
   */
  async getApprovalRules(): Promise<ApprovalRule[]> {
    try {
      const response = await apiClient.get<ApprovalRulesResponse>(
        `${API_CONFIG.BASE_URL}/approval-rules/`
      );
      return response.results;
    } catch (error) {
      console.error('Failed to fetch approval rules:', error);
      throw error;
    }
  }

  /**
   * Get a single approval rule by ID
   */
  async getApprovalRule(id: number): Promise<ApprovalRule> {
    try {
      return await apiClient.get<ApprovalRule>(
        `${API_CONFIG.BASE_URL}/approval-rules/${id}/`
      );
    } catch (error) {
      console.error(`Failed to fetch approval rule ${id}:`, error);
      throw error;
    }
  }

  /**
   * Create a new approval rule
   */
  async createApprovalRule(data: ApprovalRuleCreate): Promise<ApprovalRule> {
    try {
      return await apiClient.post<ApprovalRule>(
        `${API_CONFIG.BASE_URL}/approval-rules/`,
        data
      );
    } catch (error) {
      console.error('Failed to create approval rule:', error);
      throw error;
    }
  }

  /**
   * Update an approval rule
   */
  async updateApprovalRule(id: number, data: Partial<ApprovalRuleCreate>): Promise<ApprovalRule> {
    try {
      return await apiClient.put<ApprovalRule>(
        `${API_CONFIG.BASE_URL}/approval-rules/${id}/`,
        data
      );
    } catch (error) {
      console.error(`Failed to update approval rule ${id}:`, error);
      throw error;
    }
  }

  /**
   * Delete an approval rule
   */
  async deleteApprovalRule(id: number): Promise<void> {
    try {
      await apiClient.delete(
        `${API_CONFIG.BASE_URL}/approval-rules/${id}/`
      );
    } catch (error) {
      console.error(`Failed to delete approval rule ${id}:`, error);
      throw error;
    }
  }

  // --------------------------------------------------------------------------
  // Swap Approval Workflow
  // --------------------------------------------------------------------------

  /**
   * Get approval chain for a swap request
   */
  async getApprovalChain(swapId: number): Promise<ApprovalChain> {
    try {
      return await apiClient.get<ApprovalChain>(
        `${API_CONFIG.BASE_URL}/swap-requests/${swapId}/approval-chain/`
      );
    } catch (error) {
      console.error(`Failed to fetch approval chain for swap ${swapId}:`, error);
      throw error;
    }
  }

  /**
   * Approve a swap request at current level
   */
  async approveSwap(swapId: number, data: ApproveSwapRequest): Promise<ApprovalChain> {
    try {
      return await apiClient.post<ApprovalChain>(
        `${API_CONFIG.BASE_URL}/swap-requests/${swapId}/approve/`,
        data
      );
    } catch (error) {
      console.error(`Failed to approve swap ${swapId}:`, error);
      throw error;
    }
  }

  /**
   * Reject a swap request
   */
  async rejectSwap(swapId: number, data: RejectSwapRequest): Promise<ApprovalChain> {
    try {
      return await apiClient.post<ApprovalChain>(
        `${API_CONFIG.BASE_URL}/swap-requests/${swapId}/reject/`,
        data
      );
    } catch (error) {
      console.error(`Failed to reject swap ${swapId}:`, error);
      throw error;
    }
  }

  /**
   * Get pending approvals for current user
   */
  async getPendingApprovals(): Promise<PendingApproval[]> {
    try {
      const response = await apiClient.get<PendingApprovalsResponse>(
        `${API_CONFIG.BASE_URL}/pending-approvals/`
      );
      return response.results;
    } catch (error) {
      console.error('Failed to fetch pending approvals:', error);
      throw error;
    }
  }

  // --------------------------------------------------------------------------
  // Approval Delegations
  // --------------------------------------------------------------------------

  /**
   * Get all delegations (active and historical)
   */
  async getDelegations(): Promise<ApprovalDelegation[]> {
    try {
      const response = await apiClient.get<ApprovalDelegationsResponse>(
        `${API_CONFIG.BASE_URL}/approval-delegations/`
      );
      return response.results;
    } catch (error) {
      console.error('Failed to fetch delegations:', error);
      throw error;
    }
  }

  /**
   * Get a single delegation by ID
   */
  async getDelegation(id: number): Promise<ApprovalDelegation> {
    try {
      return await apiClient.get<ApprovalDelegation>(
        `${API_CONFIG.BASE_URL}/approval-delegations/${id}/`
      );
    } catch (error) {
      console.error(`Failed to fetch delegation ${id}:`, error);
      throw error;
    }
  }

  /**
   * Create a new delegation
   */
  async createDelegation(data: ApprovalDelegationCreate): Promise<ApprovalDelegation> {
    try {
      return await apiClient.post<ApprovalDelegation>(
        `${API_CONFIG.BASE_URL}/approval-delegations/`,
        data
      );
    } catch (error) {
      console.error('Failed to create delegation:', error);
      throw error;
    }
  }

  /**
   * Update a delegation
   */
  async updateDelegation(id: number, data: Partial<ApprovalDelegationCreate>): Promise<ApprovalDelegation> {
    try {
      return await apiClient.put<ApprovalDelegation>(
        `${API_CONFIG.BASE_URL}/approval-delegations/${id}/`,
        data
      );
    } catch (error) {
      console.error(`Failed to update delegation ${id}:`, error);
      throw error;
    }
  }

  /**
   * Delete a delegation
   */
  async deleteDelegation(id: number): Promise<void> {
    try {
      await apiClient.delete(
        `${API_CONFIG.BASE_URL}/approval-delegations/${id}/`
      );
    } catch (error) {
      console.error(`Failed to delete delegation ${id}:`, error);
      throw error;
    }
  }

  /**
   * Delegate a specific swap approval
   */
  async delegateSwapApproval(swapId: number, data: { delegate_to_user_id: number; comments?: string }): Promise<void> {
    try {
      await apiClient.post(
        `${API_CONFIG.BASE_URL}/swap-requests/${swapId}/delegate/`,
        data
      );
    } catch (error) {
      console.error(`Failed to delegate swap ${swapId}:`, error);
      throw error;
    }
  }

  // --------------------------------------------------------------------------
  // Audit Trail
  // --------------------------------------------------------------------------

  /**
   * Get audit trail for a swap request
   */
  async getAuditTrail(swapId: number): Promise<AuditTrailEntry[]> {
    try {
      const response = await apiClient.get<AuditTrailResponse>(
        `${API_CONFIG.BASE_URL}/swap-requests/${swapId}/audit-trail/`
      );
      return response.results;
    } catch (error) {
      console.error(`Failed to fetch audit trail for swap ${swapId}:`, error);
      throw error;
    }
  }
}

// Export singleton instance
const swapApprovalService = new SwapApprovalService();
export default swapApprovalService;
