'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useCreateSongFromMarkdown } from '@/hooks/queries/songs';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { UserMenu } from '@/components/auth/UserMenu';

export default function NewSongPage() {
  return (
    <AuthGuard>
      <NewSongPageContent />
    </AuthGuard>
  );
}

function NewSongPageContent() {
  const router = useRouter();
  const createSong = useCreateSongFromMarkdown();
  const [content, setContent] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!content.trim()) {
      setError('Please enter some content');
      return;
    }

    try {
      const song = await createSong.mutateAsync(content);
      router.push(`/songs/${song.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create song');
    }
  };

  const placeholder = `# Song Title

## Verse 1
First line of verse one
Second line of verse one
Third line

## Chorus
This is the chorus line
Another chorus line

## Verse 2
First line of verse two
Second line of verse two

## Bridge
Bridge lyrics here`;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="text-gray-500 hover:text-gray-700"
              >
                &larr; Back
              </Link>
              <h1 className="text-2xl font-bold text-gray-900">New Song</h1>
            </div>
            <UserMenu />
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <label
              htmlFor="content"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Song Content (Markdown)
            </label>
            <p className="text-sm text-gray-500 mb-4">
              Start with <code className="bg-gray-100 px-1 rounded"># Title</code>, then use{' '}
              <code className="bg-gray-100 px-1 rounded">## Section</code> for verses, chorus, etc.
            </p>
            <textarea
              id="content"
              rows={20}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 font-mono text-sm"
              placeholder={placeholder}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div className="flex justify-end gap-4">
            <Link
              href="/"
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={createSong.isPending}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createSong.isPending ? 'Creating...' : 'Create Song'}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
