'use client';

/**
 * Yjs Connection Test Page
 *
 * Uses dynamic import with ssr: false to avoid Turbopack bundling
 * issues with the yjs package.
 */

import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';

// Dynamically import the Yjs content component with SSR disabled
// This prevents Turbopack from trying to bundle yjs on the server
const YjsTestContent = dynamic(() => import('./YjsTestContent'), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-gray-500">Loading Yjs...</div>
    </div>
  ),
});

export default function YjsTestPage() {
  const params = useParams();
  const songId = params.id as string;

  return <YjsTestContent songId={songId} />;
}
