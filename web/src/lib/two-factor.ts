/**
 * Two-factor authentication API client.
 */

import { get, post } from './api';
import type { TwoFactorSetup, TwoFactorStatus } from '@/types/auth';

export interface MessageResponse {
  message: string;
}

export async function getTwoFactorStatus(): Promise<TwoFactorStatus> {
  return get<TwoFactorStatus>('/auth/2fa/status');
}

export async function setupTwoFactor(): Promise<TwoFactorSetup> {
  return post<TwoFactorSetup, Record<string, never>>('/auth/2fa/setup', {});
}

export async function enableTwoFactor(code: string): Promise<MessageResponse> {
  return post<MessageResponse, { code: string }>('/auth/2fa/enable', { code });
}

export async function disableTwoFactor(password: string, code: string): Promise<MessageResponse> {
  return post<MessageResponse, { password: string; code: string }>('/auth/2fa/disable', { password, code });
}
