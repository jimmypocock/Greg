/**
 * Shared constants for the songwriter app.
 */

import { SectionType } from '@/types';

/**
 * Human-readable labels for section types.
 */
export const sectionLabels: Record<SectionType, string> = {
  [SectionType.INTRO]: 'Intro',
  [SectionType.VERSE]: 'Verse',
  [SectionType.PRE_CHORUS]: 'Pre-Chorus',
  [SectionType.CHORUS]: 'Chorus',
  [SectionType.POST_CHORUS]: 'Post-Chorus',
  [SectionType.BRIDGE]: 'Bridge',
  [SectionType.OUTRO]: 'Outro',
  [SectionType.INSTRUMENTAL]: 'Instrumental',
  [SectionType.SOLO]: 'Solo',
  [SectionType.BREAKDOWN]: 'Breakdown',
  [SectionType.OTHER]: 'Other',
};

/**
 * Get the display label for a section type.
 */
export function getSectionLabel(type: SectionType): string {
  return sectionLabels[type] || type;
}
