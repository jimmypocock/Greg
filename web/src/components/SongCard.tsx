'use client';

import Link from 'next/link';
import { SongListItem } from '@/types';
import { StatusBadge } from './StatusBadge';

interface SongCardProps {
  song: SongListItem;
}

export function SongCard({ song }: SongCardProps) {
  const formattedDate = new Date(song.updated_at).toLocaleDateString();

  return (
    <Link
      href={`/songs/${song.id}`}
      className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{song.title}</h3>
          <p className="text-sm text-gray-500 mt-1">
            {song.section_count} {song.section_count === 1 ? 'section' : 'sections'}
            {song.key && ` • ${song.key}`}
            {song.tempo && ` • ${song.tempo} BPM`}
          </p>
        </div>
        <StatusBadge status={song.status} />
      </div>
      <p className="text-xs text-gray-400 mt-3">Updated {formattedDate}</p>
    </Link>
  );
}
