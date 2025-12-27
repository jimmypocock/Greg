'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import {
  useCredits,
  useSubscription,
  useCreatePortal,
  useCancelSubscription,
} from '@/hooks/queries/billing';

export function BillingSection() {
  const { user } = useAuth();
  const { data: credits, isLoading: creditsLoading } = useCredits();
  const { data: subscription, isLoading: subscriptionLoading } = useSubscription();
  const createPortal = useCreatePortal();
  const cancelSubscription = useCancelSubscription();
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const isLoading = creditsLoading || subscriptionLoading;
  const isFreePlan = !user?.plan || user.plan === 'free';

  const handleManageSubscription = () => {
    createPortal.mutate({
      return_url: `${window.location.origin}/settings`,
    });
  };

  const handleCancelSubscription = () => {
    cancelSubscription.mutate(undefined, {
      onSuccess: () => {
        setShowCancelConfirm(false);
      },
    });
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-24 bg-gray-100 rounded-lg"></div>
        <div className="h-16 bg-gray-100 rounded-lg"></div>
      </div>
    );
  }

  const creditsPercentage = credits
    ? Math.min((credits.credits_used / credits.credits_limit) * 100, 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Current Plan */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Current Plan</h3>
            <div className="mt-1 flex items-center gap-2">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                isFreePlan
                  ? 'bg-gray-100 text-gray-700'
                  : 'bg-indigo-100 text-indigo-700'
              }`}>
                {credits?.plan ? credits.plan.charAt(0).toUpperCase() + credits.plan.slice(1) : 'Free'}
              </span>
              {subscription?.cancel_at_period_end && (
                <span className="text-sm text-orange-600">
                  Cancels on {subscription.current_period_end
                    ? new Date(subscription.current_period_end).toLocaleDateString()
                    : 'period end'}
                </span>
              )}
            </div>
          </div>
          {isFreePlan ? (
            <Link
              href="/pricing"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Upgrade
            </Link>
          ) : (
            <button
              onClick={handleManageSubscription}
              disabled={createPortal.isPending}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50"
            >
              {createPortal.isPending ? 'Loading...' : 'Manage Subscription'}
            </button>
          )}
        </div>
      </div>

      {/* Credits Usage */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">AI Credits Usage</h3>

        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Credits used this period</span>
            <span className="font-medium text-gray-900">
              {credits?.credits_used || 0} / {credits?.credits_limit || 0}
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all ${
                creditsPercentage > 90
                  ? 'bg-red-500'
                  : creditsPercentage > 70
                  ? 'bg-orange-500'
                  : 'bg-indigo-600'
              }`}
              style={{ width: `${creditsPercentage}%` }}
            ></div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Credits remaining</span>
            <span className={`font-medium ${
              credits?.credits_remaining === 0 ? 'text-red-600' : 'text-green-600'
            }`}>
              {credits?.credits_remaining || 0}
              {credits?.is_unlimited && ' (Unlimited)'}
            </span>
          </div>

          {credits?.resets_at && (
            <p className="text-xs text-gray-500">
              Resets on {new Date(credits.resets_at).toLocaleDateString()}
            </p>
          )}
        </div>

        {credits?.credits_remaining === 0 && !credits?.is_unlimited && (
          <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg">
            <p className="text-sm text-red-700">
              You've used all your AI credits for this period.{' '}
              <Link href="/pricing" className="font-medium underline">
                Upgrade your plan
              </Link>{' '}
              for more credits.
            </p>
          </div>
        )}
      </div>

      {/* Cancel Subscription */}
      {subscription?.has_subscription && !subscription.cancel_at_period_end && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Cancel Subscription</h3>
          <p className="text-sm text-gray-600 mb-4">
            If you cancel, you'll retain access until the end of your current billing period.
          </p>

          {showCancelConfirm ? (
            <div className="flex items-center gap-3">
              <button
                onClick={handleCancelSubscription}
                disabled={cancelSubscription.isPending}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700"
              >
                {cancelSubscription.isPending ? 'Cancelling...' : 'Confirm Cancel'}
              </button>
              <button
                onClick={() => setShowCancelConfirm(false)}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                Never mind
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowCancelConfirm(true)}
              className="text-sm text-red-600 hover:text-red-700"
            >
              Cancel subscription
            </button>
          )}

          {cancelSubscription.isSuccess && (
            <p className="mt-3 text-sm text-green-600">
              Subscription cancelled. Access continues until period end.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
