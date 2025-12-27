/**
 * React Query hooks for billing.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  cancelSubscription,
  createCheckout,
  createPortal,
  getCredits,
  getPlans,
  getSubscription,
} from '@/lib/billing';
import { CheckoutRequest, PortalRequest } from '@/types/billing';

// Query keys
export const billingKeys = {
  all: ['billing'] as const,
  plans: () => [...billingKeys.all, 'plans'] as const,
  credits: () => [...billingKeys.all, 'credits'] as const,
  subscription: () => [...billingKeys.all, 'subscription'] as const,
};

/**
 * Get available plans.
 */
export function usePlans() {
  return useQuery({
    queryKey: billingKeys.plans(),
    queryFn: getPlans,
    staleTime: 1000 * 60 * 60, // Plans don't change often
  });
}

/**
 * Get current user's credits.
 */
export function useCredits() {
  return useQuery({
    queryKey: billingKeys.credits(),
    queryFn: getCredits,
    staleTime: 1000 * 60, // Refetch every minute
  });
}

/**
 * Get current subscription status.
 */
export function useSubscription() {
  return useQuery({
    queryKey: billingKeys.subscription(),
    queryFn: getSubscription,
    staleTime: 1000 * 60, // Refetch every minute
  });
}

/**
 * Create a checkout session and redirect to Stripe.
 */
export function useCreateCheckout() {
  return useMutation({
    mutationFn: (request: CheckoutRequest) => createCheckout(request),
    onSuccess: (data) => {
      // Redirect to Stripe checkout
      window.location.href = data.checkout_url;
    },
  });
}

/**
 * Create a customer portal session and redirect to Stripe.
 */
export function useCreatePortal() {
  return useMutation({
    mutationFn: (request: PortalRequest) => createPortal(request),
    onSuccess: (data) => {
      // Redirect to Stripe portal
      window.location.href = data.portal_url;
    },
  });
}

/**
 * Cancel subscription.
 */
export function useCancelSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: cancelSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingKeys.subscription() });
      queryClient.invalidateQueries({ queryKey: billingKeys.credits() });
    },
  });
}
