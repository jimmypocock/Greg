'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useCreateSongFromMarkdown, useQuickStartSong } from '@/hooks/queries/songs';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { UserMenu } from '@/components/auth/UserMenu';

export default function NewSongPage() {
  return (
    <AuthGuard>
      <NewSongPageContent />
    </AuthGuard>
  );
}

type NewSongMode = 'choice' | 'paste';

function NewSongPageContent() {
  const router = useRouter();
  const createSong = useCreateSongFromMarkdown();
  const quickStart = useQuickStartSong();
  const [mode, setMode] = useState<NewSongMode>('choice');
  const [content, setContent] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Handle "Explore with AI" - create empty song and redirect to editor
  const handleExplore = async () => {
    try {
      setError(null);
      const result = await quickStart.mutateAsync({});
      router.push(`/songs/${result.song_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create song');
    }
  };

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
        {mode === 'choice' ? (
          <ChoiceView
            onExplore={handleExplore}
            onPaste={() => setMode('paste')}
            isExploring={quickStart.isPending}
            exploreError={error}
          />
        ) : (
          <PasteView
            content={content}
            setContent={setContent}
            error={error}
            isSubmitting={createSong.isPending}
            placeholder={placeholder}
            onSubmit={handleSubmit}
            onBack={() => setMode('choice')}
          />
        )}
      </main>
    </div>
  );
}

interface ChoiceViewProps {
  onExplore: () => void;
  onPaste: () => void;
  isExploring?: boolean;
  exploreError?: string | null;
}

function ChoiceView({ onExplore, onPaste, isExploring, exploreError }: ChoiceViewProps) {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-10">
        <h2 className="text-3xl font-bold text-gray-900 mb-3">
          How do you want to start?
        </h2>
        <p className="text-gray-600 text-lg">
          Choose how you'd like to begin your songwriting journey
        </p>
      </div>

      {exploreError && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-700">{exploreError}</p>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {/* Explore with AI Option */}
        <button
          onClick={onExplore}
          disabled={isExploring}
          className="group relative bg-white rounded-xl border-2 border-gray-200 p-8 text-left hover:border-indigo-500 hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-wait"
        >
          <div className="absolute top-4 right-4">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
              Recommended
            </span>
          </div>

          <div className="w-14 h-14 bg-indigo-100 rounded-xl flex items-center justify-center mb-5">
            <svg className="w-7 h-7 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>

          <h3 className="text-xl font-semibold text-gray-900 mb-2 group-hover:text-indigo-600">
            Explore with AI
          </h3>
          <p className="text-gray-600 mb-4">
            Chat with our AI to discover what your song is about. Share a theme, feeling, or fragments and we'll help you shape it.
          </p>

          <div className="space-y-2 text-sm text-gray-500">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Start with any idea - theme, mood, or words
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              AI guides you, doesn't write for you
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              See your song shape build in real-time
            </div>
          </div>

          <div className="mt-6 flex items-center text-indigo-600 font-medium">
            {isExploring ? (
              <>
                <svg className="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Creating song...
              </>
            ) : (
              <>
                Start exploring
                <svg className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </>
            )}
          </div>
        </button>

        {/* Paste Lyrics Option */}
        <button
          onClick={onPaste}
          className="group bg-white rounded-xl border-2 border-gray-200 p-8 text-left hover:border-gray-400 hover:shadow-lg transition-all duration-200"
        >
          <div className="w-14 h-14 bg-gray-100 rounded-xl flex items-center justify-center mb-5">
            <svg className="w-7 h-7 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>

          <h3 className="text-xl font-semibold text-gray-900 mb-2 group-hover:text-gray-700">
            Paste Existing Lyrics
          </h3>
          <p className="text-gray-600 mb-4">
            Already have lyrics or a structure? Paste them in and we'll organize them into sections for you.
          </p>

          <div className="space-y-2 text-sm text-gray-500">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Import existing lyrics quickly
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Use simple markdown format
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Automatic section detection
            </div>
          </div>

          <div className="mt-6 flex items-center text-gray-600 font-medium">
            Paste lyrics
            <svg className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </button>
      </div>
    </div>
  );
}

interface PasteViewProps {
  content: string;
  setContent: (content: string) => void;
  error: string | null;
  isSubmitting: boolean;
  placeholder: string;
  onSubmit: (e: React.FormEvent) => void;
  onBack: () => void;
}

function PasteView({
  content,
  setContent,
  error,
  isSubmitting,
  placeholder,
  onSubmit,
  onBack,
}: PasteViewProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="flex items-center gap-4 mb-4">
        <button
          type="button"
          onClick={onBack}
          className="text-gray-500 hover:text-gray-700 flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to options
        </button>
      </div>

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
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Creating...' : 'Create Song'}
        </button>
      </div>
    </form>
  );
}
