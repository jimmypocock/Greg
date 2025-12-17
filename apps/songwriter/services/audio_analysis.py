"""
Audio analysis service using librosa.

Detects tempo and key from audio files.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import librosa
import numpy as np

logger = logging.getLogger(__name__)

# Key mapping for Krumhansl-Schmuckler algorithm
KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Krumhansl-Schmuckler key profiles
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


@dataclass
class AudioAnalysisResult:
    """Result of audio analysis."""

    tempo: Optional[float] = None
    tempo_confidence: Optional[float] = None
    key: Optional[str] = None
    key_confidence: Optional[float] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    success: bool = True


def _detect_key(y: np.ndarray, sr: int) -> tuple[str, float]:
    """
    Detect musical key using Krumhansl-Schmuckler algorithm.

    Args:
        y: Audio time series
        sr: Sample rate

    Returns:
        Tuple of (key_name, confidence)
    """
    # Compute chroma features
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)

    # Normalize
    chroma_mean = chroma_mean / np.sum(chroma_mean)

    # Test all major and minor keys
    correlations = []

    for i in range(12):
        # Rotate profiles to test each key
        major_rotated = np.roll(MAJOR_PROFILE, i)
        minor_rotated = np.roll(MINOR_PROFILE, i)

        # Normalize profiles
        major_rotated = major_rotated / np.sum(major_rotated)
        minor_rotated = minor_rotated / np.sum(minor_rotated)

        # Compute correlations
        major_corr = np.corrcoef(chroma_mean, major_rotated)[0, 1]
        minor_corr = np.corrcoef(chroma_mean, minor_rotated)[0, 1]

        correlations.append((major_corr, f"{KEY_NAMES[i]} Major"))
        correlations.append((minor_corr, f"{KEY_NAMES[i]} Minor"))

    # Find best match
    best_corr, best_key = max(correlations, key=lambda x: x[0])

    # Convert correlation to confidence (0-1 range)
    # Correlation ranges from -1 to 1, but typically for valid music it's 0.3-0.9
    confidence = max(0, min(1, (best_corr + 0.3) / 1.2))

    return best_key, confidence


def _detect_tempo(y: np.ndarray, sr: int) -> tuple[float, float]:
    """
    Detect tempo (BPM) from audio.

    Args:
        y: Audio time series
        sr: Sample rate

    Returns:
        Tuple of (tempo_bpm, confidence)
    """
    # Use librosa's beat tracker
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

    # Get tempo as float (librosa may return array)
    if hasattr(tempo, '__len__'):
        tempo = float(tempo[0]) if len(tempo) > 0 else 0.0
    else:
        tempo = float(tempo)

    # Calculate confidence based on beat consistency
    if len(beat_frames) > 1:
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        beat_intervals = np.diff(beat_times)
        if len(beat_intervals) > 0:
            interval_std = np.std(beat_intervals)
            interval_mean = np.mean(beat_intervals)
            # Lower variance = higher confidence
            cv = interval_std / interval_mean if interval_mean > 0 else 1.0
            confidence = max(0, min(1, 1 - cv))
        else:
            confidence = 0.5
    else:
        confidence = 0.3

    return tempo, confidence


def analyze_audio(file_path: Path) -> AudioAnalysisResult:
    """
    Analyze an audio file to detect tempo and key.

    Args:
        file_path: Path to the audio file

    Returns:
        AudioAnalysisResult with detected values
    """
    try:
        logger.info(f"Loading audio file: {file_path}")

        # Load audio file
        y, sr = librosa.load(file_path, sr=None, mono=True)

        # Get duration
        duration = librosa.get_duration(y=y, sr=sr)
        logger.info(f"Audio loaded: {duration:.1f}s, sr={sr}")

        # Detect tempo
        logger.info("Detecting tempo...")
        tempo, tempo_confidence = _detect_tempo(y, sr)
        logger.info(f"Tempo: {tempo:.1f} BPM (confidence: {tempo_confidence:.2f})")

        # Detect key
        logger.info("Detecting key...")
        key, key_confidence = _detect_key(y, sr)
        logger.info(f"Key: {key} (confidence: {key_confidence:.2f})")

        return AudioAnalysisResult(
            tempo=round(tempo, 1),
            tempo_confidence=round(tempo_confidence, 3),
            key=key,
            key_confidence=round(key_confidence, 3),
            duration_seconds=round(duration, 2),
            success=True,
        )

    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        return AudioAnalysisResult(
            success=False,
            error=str(e),
        )
