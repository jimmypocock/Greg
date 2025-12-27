/**
 * Admin types for the Songwriter app.
 */

export interface AdminUser {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface UserListResponse {
  users: AdminUser[];
  total: number;
}

export interface UserResponse {
  user: AdminUser;
}

export interface UserUpdateRequest {
  is_active?: boolean;
  role?: string;
}

export interface InviteDetail {
  code: string;
  email: string | null;
  is_active: boolean;
  created_at: string;
  expires_at: string | null;
  used_at: string | null;
  used_by: string | null;
  created_by: string;
}

export interface InviteResponse {
  invite: InviteDetail;
  signup_url: string | null;
}

export interface InviteListResponse {
  invites: InviteDetail[];
  total: number;
}

export interface InviteCreateRequest {
  email?: string | null;
  expires_in_days?: number;
}

export interface DailyCost {
  date: string;
  provider: string;
  model: string;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_tokens: number;
  total_input_cost_usd: string;
  total_output_cost_usd: string;
  total_cost_usd: string;
  avg_latency_ms: number | null;
}

export interface CostSummary {
  period_start: string;
  period_end: string;
  total_cost_usd: string;
  total_requests: number;
  daily_breakdown: DailyCost[];
}

export interface MessageResponse {
  message: string;
}
