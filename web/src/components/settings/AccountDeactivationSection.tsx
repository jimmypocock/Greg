'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { del, ApiError } from '@/lib/api';

interface DeactivateRequest {
  password: string;
  confirmation: string;
}

interface MessageResponse {
  message: string;
}

export function AccountDeactivationSection() {
  const router = useRouter();
  const [isExpanded, setIsExpanded] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDeactivate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (confirmation !== 'DELETE') {
      setError('Please type DELETE to confirm');
      return;
    }

    setIsLoading(true);

    try {
      await del<MessageResponse>('/auth/me', {
        password,
        confirmation,
      } as DeactivateRequest);

      // Clear tokens from localStorage
      localStorage.removeItem('songwriter_access_token');
      localStorage.removeItem('songwriter_refresh_token');

      // Redirect to login with a message
      router.push('/login?deactivated=true');
    } catch (err) {
      if (err instanceof ApiError) {
        // Parse the error detail from the response
        try {
          const errorData = JSON.parse(err.message);
          setError(errorData.detail || 'Failed to deactivate account');
        } catch {
          setError(err.message || 'Failed to deactivate account');
        }
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setIsExpanded(false);
    setPassword('');
    setConfirmation('');
    setError('');
  };

  return (
    <div className="bg-white border border-red-200 rounded-lg p-6">
      <h3 className="text-lg font-medium text-red-900 mb-2">Danger Zone</h3>

      {!isExpanded ? (
        <>
          <p className="text-sm text-gray-600 mb-4">
            Deactivating your account will anonymize your data and prevent you from logging in.
            Your data will be retained but your email and personal information will be removed.
          </p>
          <button
            onClick={() => setIsExpanded(true)}
            className="inline-flex items-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md shadow-sm text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            Deactivate Account
          </button>
        </>
      ) : (
        <form onSubmit={handleDeactivate} className="space-y-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Warning</h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>This action will:</p>
                  <ul className="list-disc list-inside mt-1 space-y-1">
                    <li>Deactivate your account immediately</li>
                    <li>Anonymize your email address</li>
                    <li>Cancel any active subscriptions</li>
                    <li>Revoke all active sessions</li>
                  </ul>
                  <p className="mt-2 font-medium">This action cannot be undone.</p>
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div>
            <label htmlFor="deactivate-password" className="block text-sm font-medium text-gray-700">
              Enter your password to confirm
            </label>
            <input
              type="password"
              id="deactivate-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500 sm:text-sm"
              placeholder="Your password"
            />
          </div>

          <div>
            <label htmlFor="deactivate-confirmation" className="block text-sm font-medium text-gray-700">
              Type <span className="font-mono font-bold text-red-600">DELETE</span> to confirm
            </label>
            <input
              type="text"
              id="deactivate-confirmation"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500 sm:text-sm font-mono"
              placeholder="DELETE"
            />
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleCancel}
              className="flex-1 px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || confirmation !== 'DELETE' || !password}
              className="flex-1 px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Deactivating...
                </span>
              ) : (
                'Deactivate Account'
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
