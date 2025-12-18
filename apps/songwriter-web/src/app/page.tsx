'use client';

import Link from 'next/link';
import { useSongs } from '@/hooks/queries/songs';
import { SongCard } from '@/components/SongCard';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { UserMenu } from '@/components/auth/UserMenu';

export default function Home() {
  return (
    <AuthGuard>
      <HomeContent />
    </AuthGuard>
  );
}

function HomeContent() {
  const { data, isLoading, error } = useSongs();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Songwriter</h1>
            <div className="flex items-center gap-4">
              <Link
                href="/songs/new"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                New Song
              </Link>
              <UserMenu />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="mt-2 text-sm text-gray-500">Loading songs...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-red-800">Error loading songs</h3>
            <p className="mt-1 text-sm text-red-700">
              {error instanceof Error ? error.message : 'Unknown error'}
            </p>
            <p className="mt-2 text-xs text-red-600">
              Make sure the Songwriter API is running on port 8081
            </p>
          </div>
        ) : data?.songs.length === 0 ? (
          <div className="text-center py-12">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No songs yet</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating a new song.
            </p>
            <div className="mt-6">
              <Link
                href="/songs/new"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700"
              >
                Create your first song
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">
                Your Songs ({data?.total || 0})
              </h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {data?.songs.map((song) => (
                <SongCard key={song.id} song={song} />
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
