/**
 * Billing types for the Songwriter app.
 */

export interface PlanInfo {
  id: string;
  name: string;
  price_monthly: number; // In cents
  credits_per_month: number;
  features: string[];
}

export interface PlansResponse {
  plans: PlanInfo[];
}

export interface CreditsInfo {
  plan: string;
  credits_used: number;
  credits_limit: number;
  credits_remaining: number;
  resets_at: string;
  is_unlimited: boolean;
}

export interface CheckoutRequest {
  success_url: string;
  cancel_url: string;
  plan: 'pro' | 'enterprise';
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalRequest {
  return_url: string;
}

export interface PortalResponse {
  portal_url: string;
}

export interface SubscriptionPlan {
  id: string;
  product: string;
  amount: number;
  currency: string;
  interval: string;
}

export interface SubscriptionStatus {
  has_subscription: boolean;
  status: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  plan: SubscriptionPlan | null;
}

export interface CancelResponse {
  cancelled: boolean;
  message: string;
}
