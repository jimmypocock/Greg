'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { usePlans, useCreateCheckout } from '@/hooks/queries/billing';

const CheckIcon = () => (
  <svg className="h-5 w-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

export default function PricingPage() {
  const { isAuthenticated, user, isLoading: authLoading } = useAuth();
  const { data: plansData, isLoading: plansLoading } = usePlans();
  const createCheckout = useCreateCheckout();

  const plans = plansData?.plans || [];

  const handleUpgrade = (planId: string) => {
    if (!isAuthenticated) {
      window.location.href = '/register';
      return;
    }

    if (planId === 'free') return;

    createCheckout.mutate({
      plan: planId as 'pro' | 'enterprise',
      success_url: `${window.location.origin}/settings?success=true`,
      cancel_url: `${window.location.origin}/pricing`,
    });
  };

  const isLoading = authLoading || plansLoading;

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <svg
                className="h-8 w-8 text-indigo-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                />
              </svg>
              <span className="text-xl font-bold text-white">Songwriter</span>
            </Link>
            <nav className="flex items-center gap-4">
              {isAuthenticated ? (
                <Link
                  href="/dashboard"
                  className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
                >
                  Dashboard
                </Link>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
                  >
                    Sign in
                  </Link>
                  <Link
                    href="/register"
                    className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
                  >
                    Get Started
                  </Link>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-white mb-4">
            Simple, transparent pricing
          </h1>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            Choose the plan that fits your songwriting needs. Upgrade or downgrade anytime.
          </p>
        </div>

        {/* Pricing Cards */}
        {isLoading ? (
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
          </div>
        ) : (
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {plans.map((plan) => {
              const isCurrentPlan = user?.plan === plan.id;
              const isPro = plan.id === 'pro';

              return (
                <div
                  key={plan.id}
                  className={`relative rounded-2xl border ${
                    isPro
                      ? 'border-indigo-500 bg-gray-800/50'
                      : 'border-gray-700 bg-gray-800/30'
                  } p-8`}
                >
                  {isPro && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-indigo-500 text-white">
                        Most Popular
                      </span>
                    </div>
                  )}

                  <div className="text-center mb-8">
                    <h3 className="text-xl font-semibold text-white mb-2">{plan.name}</h3>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-4xl font-bold text-white">
                        ${(plan.price_monthly / 100).toFixed(0)}
                      </span>
                      <span className="text-gray-400">/month</span>
                    </div>
                    <p className="mt-2 text-sm text-gray-400">
                      {plan.credits_per_month} AI credits per month
                    </p>
                  </div>

                  <ul className="space-y-4 mb-8">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="flex items-start gap-3">
                        <CheckIcon />
                        <span className="text-sm text-gray-300">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <button
                    onClick={() => handleUpgrade(plan.id)}
                    disabled={isCurrentPlan || createCheckout.isPending}
                    className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
                      isCurrentPlan
                        ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                        : isPro
                        ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                        : 'bg-gray-700 text-white hover:bg-gray-600'
                    }`}
                  >
                    {isCurrentPlan
                      ? 'Current Plan'
                      : createCheckout.isPending
                      ? 'Loading...'
                      : plan.id === 'free'
                      ? 'Get Started'
                      : 'Upgrade'}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* FAQ or Additional Info */}
        <div className="mt-16 text-center">
          <p className="text-gray-400">
            All plans include full access to song editing and organization features.
            <br />
            AI credits are used for feedback, chord suggestions, and other AI-powered features.
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            Songwriter - AI-powered songwriting assistant
          </p>
        </div>
      </footer>
    </div>
  );
}
