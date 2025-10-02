import { User, LoginCredentials } from '../types';
import { apiClient } from './apiClient';
import { clearPermissionsCache } from '../hooks/usePermissions';

class AuthService {
  async login(credentials: LoginCredentials): Promise<{ user?: User; token?: string; mfa_required?: boolean; user_id?: number; username?: string }> {
    // Use new login endpoint that checks for MFA
    const response: any = await apiClient.post('/api/auth/login/', credentials);
    
    if (response.mfa_required) {
      // MFA is required - return flag
      return {
        mfa_required: true,
        user_id: response.user_id,
        username: response.username
      };
    }
    
    // No MFA required - get user info and return token
    localStorage.setItem('token', response.token);
    const user = await this.getCurrentUser();
    
    return { user, token: response.token, mfa_required: false };
  }

  async getCurrentUser(): Promise<User> {
    return apiClient.getCurrentUser();
  }

  async logout(): Promise<void> {
    clearPermissionsCache();
    await apiClient.logout();
  }
}

export default new AuthService();
