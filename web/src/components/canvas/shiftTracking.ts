/**
 * Global Shift key state tracking
 *
 * Tracks whether the Shift key is held down and notifies listeners.
 * Used to enable drag mode when Shift+hovering over gutters.
 */

let isShiftHeld = false;
const shiftListeners = new Set<() => void>();
let shiftTrackingInitialized = false;

/**
 * Initialize the global Shift key tracking.
 * Safe to call multiple times - will only initialize once.
 */
export function initShiftTracking() {
  if (typeof window === 'undefined') return;
  if (shiftTrackingInitialized) return;
  shiftTrackingInitialized = true;

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Shift' && !isShiftHeld) {
      isShiftHeld = true;
      shiftListeners.forEach(fn => fn());
    }
  };

  const handleKeyUp = (e: KeyboardEvent) => {
    if (e.key === 'Shift' && isShiftHeld) {
      isShiftHeld = false;
      shiftListeners.forEach(fn => fn());
    }
  };

  // Also handle blur (user switches windows while holding Shift)
  const handleBlur = () => {
    if (isShiftHeld) {
      isShiftHeld = false;
      shiftListeners.forEach(fn => fn());
    }
  };

  document.addEventListener('keydown', handleKeyDown);
  document.addEventListener('keyup', handleKeyUp);
  window.addEventListener('blur', handleBlur);
}

/**
 * Check if the Shift key is currently held down.
 */
export function getIsShiftHeld(): boolean {
  return isShiftHeld;
}

/**
 * Subscribe to Shift key state changes.
 * Returns an unsubscribe function.
 */
export function subscribeToShift(listener: () => void): () => void {
  shiftListeners.add(listener);
  return () => {
    shiftListeners.delete(listener);
  };
}

// Initialize on module load (if in browser)
initShiftTracking();
