'use client';

import { useState, useEffect } from 'react';
import { get } from '@/lib/api';

interface ReferralCode {
  code: string;
  url: string;
}

interface ReferralStats {
  referral_count: number;
  credits_earned: number;
}

export function ReferralSection() {
  const [copied, setCopied] = useState(false);
  const [referralCode, setReferralCode] = useState<ReferralCode | null>(null);
  const [stats, setStats] = useState<ReferralStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [codeData, statsData] = await Promise.all([
          get<ReferralCode>('/billing/referral-code'),
          get<ReferralStats>('/billing/referral-stats'),
        ]);
        setReferralCode(codeData);
        setStats(statsData);
      } catch (err) {
        console.error('Failed to fetch referral data:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleCopy = async () => {
    if (!referralCode?.url) return;

    try {
      await navigator.clipboard.writeText(referralCode.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const input = document.createElement('input');
      input.value = referralCode.url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="bg-white border border-gray-200 rounded-lg p-6 animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-10 bg-gray-200 rounded w-full"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* How it works */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-3">
          Earn Credits by Referring Friends
        </h3>
        <div className="grid sm:grid-cols-2 gap-4 text-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
              <span className="text-indigo-600 font-medium">1</span>
            </div>
            <div>
              <p className="font-medium text-gray-900">Share your link</p>
              <p className="text-gray-600">Send your referral link to friends</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
              <span className="text-indigo-600 font-medium">2</span>
            </div>
            <div>
              <p className="font-medium text-gray-900">They sign up</p>
              <p className="text-gray-600">They join and start creating</p>
            </div>
          </div>
          <div className="flex items-start gap-3 sm:col-span-2 sm:justify-center">
            <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
              <span className="text-green-600 font-medium">3</span>
            </div>
            <div>
              <p className="font-medium text-gray-900">You earn credits</p>
              <p className="text-gray-600">Get 5 bonus AI credits for each referral</p>
            </div>
          </div>
        </div>
      </div>

      {/* Referral Link */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Your Referral Link</h3>

        <div className="flex gap-2">
          <input
            type="text"
            readOnly
            value={referralCode?.url || ''}
            className="flex-1 px-4 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg text-gray-600"
          />
          <button
            onClick={handleCopy}
            disabled={!referralCode}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              copied
                ? 'bg-green-100 text-green-700'
                : 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50'
            }`}
          >
            {copied ? (
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Copied!
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                </svg>
                Copy
              </span>
            )}
          </button>
        </div>

        <div className="mt-4 text-sm text-gray-500">
          <p>Your referral code: <span className="font-mono font-medium text-gray-700">{referralCode?.code || '...'}</span></p>
        </div>
      </div>

      {/* Stats */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Your Referral Stats</h3>
        <div className="grid grid-cols-2 gap-6">
          <div className="text-center">
            <p className="text-3xl font-bold text-indigo-600">{stats?.referral_count ?? 0}</p>
            <p className="text-sm text-gray-600">Successful Referrals</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-green-600">{stats?.credits_earned ?? 0}</p>
            <p className="text-sm text-gray-600">Credits Earned</p>
          </div>
        </div>
        <p className="mt-4 text-xs text-gray-500 text-center">
          Credits are applied instantly when friends sign up with your code
        </p>
      </div>
    </div>
  );
}
