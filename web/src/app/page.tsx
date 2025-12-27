'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';

export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
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
            </div>
            <nav className="flex items-center gap-4">
              {isLoading ? (
                <div className="h-9 w-20 bg-gray-800 rounded animate-pulse" />
              ) : isAuthenticated ? (
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

      {/* Hero Section */}
      <main>
        <div className="max-w-6xl mx-auto px-4 py-24 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight">
              Your AI-Powered
              <span className="block text-indigo-500">Songwriting Partner</span>
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto">
              Write better songs with intelligent feedback. Get real-time critiques,
              explore chord progressions, and refine your lyrics with an AI that
              understands music.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              {isLoading ? (
                <div className="h-12 w-40 bg-gray-800 rounded-lg animate-pulse" />
              ) : isAuthenticated ? (
                <Link
                  href="/dashboard"
                  className="inline-flex items-center px-8 py-3 text-base font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
                >
                  Go to Dashboard
                </Link>
              ) : (
                <>
                  <Link
                    href="/register"
                    className="inline-flex items-center px-8 py-3 text-base font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
                  >
                    Start Writing
                  </Link>
                  <Link
                    href="/login"
                    className="inline-flex items-center px-8 py-3 text-base font-medium rounded-lg text-gray-300 border border-gray-700 hover:bg-gray-800 transition-colors"
                  >
                    Sign in
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="border-t border-gray-800">
          <div className="max-w-6xl mx-auto px-4 py-24 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center p-6">
                <div className="w-12 h-12 mx-auto mb-4 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                  <svg className="h-6 w-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">Write & Organize</h3>
                <p className="text-gray-400">
                  Structure your songs with verses, choruses, and bridges.
                  Keep multiple versions as you refine your work.
                </p>
              </div>

              <div className="text-center p-6">
                <div className="w-12 h-12 mx-auto mb-4 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                  <svg className="h-6 w-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">AI Feedback</h3>
                <p className="text-gray-400">
                  Get constructive critiques on your lyrics, structure, and flow
                  from AI agents trained to help songwriters improve.
                </p>
              </div>

              <div className="text-center p-6">
                <div className="w-12 h-12 mx-auto mb-4 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                  <svg className="h-6 w-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">Chord Charts</h3>
                <p className="text-gray-400">
                  Place chords above your lyrics and generate chord sheets.
                  Upload audio to detect tempo, key, and progressions.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="border-t border-gray-800 bg-gray-800/30">
          <div className="max-w-6xl mx-auto px-4 py-16 sm:px-6 lg:px-8 text-center">
            <h2 className="text-2xl font-bold text-white mb-4">
              Ready to write your next song?
            </h2>
            <p className="text-gray-400 mb-8">
              {isAuthenticated
                ? "Head to your dashboard to start a new song."
                : "Create an account with an invite code to get started."}
            </p>
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className="inline-flex items-center px-6 py-3 text-base font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
              >
                Go to Dashboard
              </Link>
            ) : (
              <Link
                href="/register"
                className="inline-flex items-center px-6 py-3 text-base font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
              >
                Get Started
              </Link>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center gap-4">
            <div className="flex gap-6 text-sm text-gray-500">
              <Link href="/terms" className="hover:text-gray-400">Terms of Service</Link>
              <Link href="/privacy" className="hover:text-gray-400">Privacy Policy</Link>
            </div>
            <p className="text-sm text-gray-500">
              Songwriter - AI-powered songwriting assistant
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
