/**
 * Authentication types for the Songwriter app.
 */

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

export interface LoginCredentials {
  username: string; // FastAPI-Users uses username for email
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  invite_code?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
