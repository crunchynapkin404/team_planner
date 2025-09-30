import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { ApiError } from '../types';
import { API_CONFIG } from '../config/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: 60000, // Increased to 60 seconds for orchestrator operations
      withCredentials: false, // Disable credentials to avoid CSRF issues with token auth
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token && config.headers) {
          config.headers.Authorization = `Token ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle errors
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response;
      },
      (error) => {
        const apiError: ApiError = {
          message: error.response?.data?.detail || error.message || 'An error occurred',
          status: error.response?.status || 500,
          data: error.response?.data,
        };

        // Handle auth errors
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
        }

        return Promise.reject(apiError);
      }
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  // Authentication methods
  async login(username: string, password: string): Promise<{ token: string }> {
    const response = await this.post<{ token: string }>(API_CONFIG.ENDPOINTS.AUTH_TOKEN, {
      username,
      password,
    });
    
    // Store token
    localStorage.setItem('token', response.token);
    
    return response;
  }

  async logout(): Promise<void> {
    try {
      await this.post(API_CONFIG.ENDPOINTS.AUTH_LOGOUT);
    } finally {
      localStorage.removeItem('token');
    }
  }

  async getCurrentUser(): Promise<any> {
    return this.get(API_CONFIG.ENDPOINTS.USERS_ME);
  }

  // Helper to check if user is authenticated
  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }

  // Get stored token
  getToken(): string | null {
    return localStorage.getItem('token');
  }
}

export const apiClient = new ApiClient();
