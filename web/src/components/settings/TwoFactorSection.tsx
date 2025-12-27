'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import {
  getTwoFactorStatus,
  setupTwoFactor,
  enableTwoFactor,
  disableTwoFactor,
} from '@/lib/two-factor';
import type { TwoFactorSetup } from '@/types/auth';

type SetupStep = 'idle' | 'setup' | 'verify';

export function TwoFactorSection() {
  const { user } = useAuth();
  const [isEnabled, setIsEnabled] = useState(user?.totp_enabled ?? false);
  const [setupStep, setSetupStep] = useState<SetupStep>('idle');
  const [setupData, setSetupData] = useState<TwoFactorSetup | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [password, setPassword] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showDisableForm, setShowDisableForm] = useState(false);

  useEffect(() => {
    // Fetch current 2FA status
    getTwoFactorStatus()
      .then((status) => setIsEnabled(status.enabled))
      .catch(() => {});
  }, []);

  const handleSetup = async () => {
    setError('');
    setIsLoading(true);

    try {
      const data = await setupTwoFactor();
      setSetupData(data);
      setSetupStep('setup');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to setup 2FA');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      await enableTwoFactor(verificationCode);
      setIsEnabled(true);
      setSetupStep('idle');
      setSetupData(null);
      setVerificationCode('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid verification code');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisable = async () => {
    if (!password || !disableCode) {
      setError('Please enter your password and a verification code');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      await disableTwoFactor(password, disableCode);
      setIsEnabled(false);
      setShowDisableForm(false);
      setPassword('');
      setDisableCode('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disable 2FA');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setSetupStep('idle');
    setSetupData(null);
    setVerificationCode('');
    setError('');
    setShowDisableForm(false);
    setPassword('');
    setDisableCode('');
  };

  // Code input handler - auto-focus next input
  const handleCodeChange = (value: string, setter: (v: string) => void) => {
    const cleaned = value.replace(/\D/g, '').slice(0, 6);
    setter(cleaned);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Two-Factor Authentication</h3>
          <p className="text-sm text-gray-600 mt-1">
            Add an extra layer of security to your account using an authenticator app.
          </p>
        </div>
        {isEnabled && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            Enabled
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Not enabled - show setup button */}
      {!isEnabled && setupStep === 'idle' && (
        <button
          onClick={handleSetup}
          disabled={isLoading}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isLoading ? 'Setting up...' : 'Set up 2FA'}
        </button>
      )}

      {/* Setup step - show QR code */}
      {!isEnabled && setupStep === 'setup' && setupData && (
        <div className="space-y-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <p className="text-sm text-gray-700 mb-3">
              Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.):
            </p>
            <div className="flex justify-center mb-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={setupData.qr_code}
                alt="2FA QR Code"
                className="border border-gray-200 rounded-lg"
                width={200}
                height={200}
              />
            </div>
            <p className="text-xs text-gray-500 text-center">
              Or enter this code manually: <code className="bg-gray-200 px-1 rounded">{setupData.secret}</code>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Enter the 6-digit code from your authenticator app
            </label>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={verificationCode}
              onChange={(e) => handleCodeChange(e.target.value, setVerificationCode)}
              placeholder="000000"
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-center text-lg tracking-widest font-mono"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleVerify}
              disabled={isLoading || verificationCode.length !== 6}
              className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {isLoading ? 'Verifying...' : 'Verify & Enable'}
            </button>
            <button
              onClick={handleCancel}
              disabled={isLoading}
              className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Enabled - show disable button */}
      {isEnabled && !showDisableForm && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Your account is protected with two-factor authentication. You&apos;ll need to enter a code from your authenticator app when signing in.
          </p>
          <button
            onClick={() => setShowDisableForm(true)}
            className="inline-flex items-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            Disable 2FA
          </button>
        </div>
      )}

      {/* Disable form */}
      {isEnabled && showDisableForm && (
        <div className="space-y-4 border-t border-gray-200 pt-4 mt-4">
          <p className="text-sm text-gray-700">
            To disable two-factor authentication, enter your password and a code from your authenticator app:
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Authenticator Code
            </label>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={disableCode}
              onChange={(e) => handleCodeChange(e.target.value, setDisableCode)}
              placeholder="000000"
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-center text-lg tracking-widest font-mono"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleDisable}
              disabled={isLoading || !password || disableCode.length !== 6}
              className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
            >
              {isLoading ? 'Disabling...' : 'Disable 2FA'}
            </button>
            <button
              onClick={handleCancel}
              disabled={isLoading}
              className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
