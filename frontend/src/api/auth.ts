import { apiClient } from './client';

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  refresh_token?: string;
  expires_in?: number;
  user: User;
}

export const authAPI = {
  login: (email: string, password: string) =>
    apiClient.post<LoginResponse>('/auth/login', 
      new URLSearchParams({
        username: email,
        password: password,
      }).toString(),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    ),
  
  register: (name: string, email: string, password: string) =>
    apiClient.post<LoginResponse>('/auth/register', { name, email, password }),
  
  resetPassword: (email: string) =>
    apiClient.post('/auth/password-reset-request', { email }),

  getMe: () =>
    apiClient.get<User>('/auth/me'),
};