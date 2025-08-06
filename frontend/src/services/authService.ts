import { User, LoginCredentials } from '../types';
import { apiClient } from './apiClient';

class AuthService {
  async login(credentials: LoginCredentials): Promise<{ user: User; token: string }> {
    const response = await apiClient.login(credentials.username, credentials.password);
    
    // Get user info after successful login
    const user = await this.getCurrentUser();
    
    return { user, token: response.token };
  }

  async getCurrentUser(): Promise<User> {
    return apiClient.getCurrentUser();
  }

  async logout(): Promise<void> {
    await apiClient.logout();
  }
}

export default new AuthService();
