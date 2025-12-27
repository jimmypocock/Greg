/**
 * Billing API functions for the Songwriter app.
 */

import { get, post } from './api';
import {
  CancelResponse,
  CheckoutRequest,
  CheckoutResponse,
  CreditsInfo,
  PlansResponse,
  PortalRequest,
  PortalResponse,
  SubscriptionStatus,
} from '@/types/billing';

/**
 * Get available subscription plans.
 */
export async function getPlans(): Promise<PlansResponse> {
  return get<PlansResponse>('/billing/plans');
}

/**
 * Get current user's credits information.
 */
export async function getCredits(): Promise<CreditsInfo> {
  return get<CreditsInfo>('/billing/credits');
}

/**
 * Get current subscription status.
 */
export async function getSubscription(): Promise<SubscriptionStatus> {
  return get<SubscriptionStatus>('/billing/subscription');
}

/**
 * Create a Stripe checkout session.
 */
export async function createCheckout(request: CheckoutRequest): Promise<CheckoutResponse> {
  return post<CheckoutResponse, CheckoutRequest>('/billing/checkout', request);
}

/**
 * Create a Stripe customer portal session.
 */
export async function createPortal(request: PortalRequest): Promise<PortalResponse> {
  return post<PortalResponse, PortalRequest>('/billing/portal', request);
}

/**
 * Cancel subscription at end of billing period.
 */
export async function cancelSubscription(): Promise<CancelResponse> {
  return post<CancelResponse, Record<string, never>>('/billing/cancel', {});
}
