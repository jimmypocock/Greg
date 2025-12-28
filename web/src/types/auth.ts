/**
 * Authentication types for the Songwriter app.
 */

export type UserPlan = 'free' | 'pro';
export type UserRole = 'user' | 'admin';

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  role: UserRole;
  plan: UserPlan;
  ai_credits_used: number;
  ai_credits_limit: number;
  ai_credits_remaining: number;
  totp_enabled: boolean;
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
  requires_2fa?: boolean;
  temp_token?: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// 2FA types
export interface TwoFactorStatus {
  enabled: boolean;
}

export interface TwoFactorSetup {
  secret: string;
  qr_code: string;
  otpauth_uri: string;
}

export interface TwoFactorVerifyRequest {
  temp_token: string;
  code: string;
}
