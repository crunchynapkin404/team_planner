/**
 * Service for managing shift templates.
 */

import { apiClient } from './apiClient';

export interface ShiftTemplate {
  id: number;
  name: string;
  shift_type: string;
  shift_type_display: string;
  description: string;
  duration_hours: number;
  skills_required: Array<{
    id: number;
    name: string;
  }>;
  is_active: boolean;
  category: string;
  tags: string[];
  is_favorite: boolean;
  usage_count: number;
  created_by: {
    id: number;
    username: string;
  } | null;
  default_start_time: string | null;
  default_end_time: string | null;
  notes: string;
  created: string;
}

export interface ShiftTemplateCreate {
  name: string;
  shift_type: string;
  description?: string;
  duration_hours: number;
  skill_ids?: number[];
  is_active?: boolean;
  category?: string;
  tags?: string[];
  is_favorite?: boolean;
  default_start_time?: string;
  default_end_time?: string;
  notes?: string;
}

export const templateService = {
  /**
   * List all shift templates with optional filters.
   */
  async listTemplates(filters?: {
    shift_type?: string;
    category?: string;
    is_active?: boolean;
    is_favorite?: boolean;
    search?: string;
  }): Promise<ShiftTemplate[]> {
    const params = new URLSearchParams();
    
    if (filters?.shift_type) params.append('shift_type', filters.shift_type);
    if (filters?.category) params.append('category', filters.category);
    if (filters?.is_active !== undefined) params.append('is_active', filters.is_active.toString());
    if (filters?.is_favorite !== undefined) params.append('is_favorite', filters.is_favorite.toString());
    if (filters?.search) params.append('search', filters.search);
    
    const queryString = params.toString();
    const url = queryString ? `/templates/?${queryString}` : '/templates/';
    
    const response: any = await apiClient.get(url);
    return Array.isArray(response) ? response : (response?.results || response || []);
  },

  /**
   * Get a single template by ID.
   */
  async getTemplate(id: number): Promise<ShiftTemplate> {
    const response: any = await apiClient.get(`/templates/${id}/`);
    return response;
  },

  /**
   * Create a new shift template.
   */
  async createTemplate(data: ShiftTemplateCreate): Promise<{ id: number; message: string }> {
    const response: any = await apiClient.post('/templates/', data);
    return response;
  },

  /**
   * Update an existing shift template.
   */
  async updateTemplate(id: number, data: Partial<ShiftTemplateCreate>): Promise<{ message: string }> {
    const response: any = await apiClient.put(`/templates/${id}/`, data);
    return response;
  },

  /**
   * Delete a shift template.
   */
  async deleteTemplate(id: number): Promise<void> {
    await apiClient.delete(`/templates/${id}/`);
  },

  /**
   * Clone an existing template.
   */
  async cloneTemplate(id: number): Promise<{ id: number; message: string }> {
    const response: any = await apiClient.post(`/templates/${id}/clone/`, {});
    return response;
  },

  /**
   * Toggle favorite status of a template.
   */
  async toggleFavorite(id: number): Promise<{ message: string; is_favorite: boolean }> {
    const response: any = await apiClient.post(`/templates/${id}/favorite/`, {});
    return response;
  },
};

export default templateService;
