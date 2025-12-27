"""
Audio analysis service using librosa and optionally madmom.

Detects tempo, key, time signature, chords, and beat positions from audio files.

Basic analysis (tempo, key, duration) uses librosa and is always available.
Extended analysis (time signature, chords, beats) requires madmom which is optional.

To install madmom:
    uv pip install Cython numpy
    uv pip install madmom --no-build-isolation
"""

import collections
import collections.abc
import json
import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import librosa
import numpy as np

# Python 3.10+ compatibility fix for madmom
# MutableSequence moved from collections to collections.abc
if not hasattr(collections, 'MutableSequence'):
    collections.MutableSequence = collections.abc.MutableSequence

# NumPy 1.24+ compatibility fix for madmom
# np.float, np.int, etc. were removed - suppress FutureWarnings for these
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    if not hasattr(np, 'float'):
        np.float = np.float64
    if not hasattr(np, 'int'):
        np.int = np.int64
    if not hasattr(np, 'complex'):
        np.complex = np.complex128
    if not hasattr(np, 'object'):
        np.object = np.object_
    if not hasattr(np, 'bool'):
        np.bool = np.bool_
    if not hasattr(np, 'str'):
        np.str = np.str_

logger = logging.getLogger(__name__)

# Check if madmom is available
try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="madmom")
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")
        import madmom  # noqa: F401
    MADMOM_AVAILABLE = True
    logger.info("madmom is available - extended audio analysis enabled")
except ImportError as e:
    MADMOM_AVAILABLE = False
    logger.info(f"madmom not available: {e} - using basic audio analysis only")

# Key mapping for Krumhansl-Schmuckler algorithm
KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Krumhansl-Schmuckler key profiles
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


@dataclass
class ChordSegment:
    """A chord detected at a specific time range."""

    start: float
    end: float
    chord: str


@dataclass
class AudioAnalysisResult:
    """Result of audio analysis."""

    # Core analysis (librosa)
    tempo: Optional[float] = None
    tempo_confidence: Optional[float] = None
    key: Optional[str] = None
    key_confidence: Optional[float] = None
    duration_seconds: Optional[float] = None

    # Extended analysis (madmom)
    time_signature: Optional[str] = None
    time_signature_confidence: Optional[float] = None
    chords: list[ChordSegment] = field(default_factory=list)
    beat_positions: list[float] = field(default_factory=list)

    # Status
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


def _convert_to_wav_for_madmom(file_path: Path) -> Path | None:
    """
    Convert audio file to WAV format for madmom compatibility.

    Madmom has trouble loading m4a and some mp3 files without ffmpeg.
    We use soundfile (via librosa) to convert to a temp wav file.

    Returns:
        Path to temp wav file, or None if conversion fails
    """
    import tempfile
    import soundfile as sf

    try:
        # Load with librosa (handles many formats)
        y, sr = librosa.load(file_path, sr=44100, mono=True)

        # Write to temp wav file
        temp_dir = Path(tempfile.gettempdir())
        temp_wav = temp_dir / f"madmom_temp_{file_path.stem}.wav"
        sf.write(str(temp_wav), y, sr)

        return temp_wav
    except Exception as e:
        logger.warning(f"Failed to convert {file_path} to wav: {e}")
        return None


def _detect_time_signature_madmom(file_path: Path) -> tuple[str, float]:
    """
    Detect time signature using madmom's downbeat tracking.

    Args:
        file_path: Path to audio file

    Returns:
        Tuple of (time_signature, confidence)
    """
    if not MADMOM_AVAILABLE:
        return "4/4", 0.5  # Default with low confidence

    # Convert to wav if needed (madmom struggles with m4a without ffmpeg)
    wav_path = file_path
    temp_wav = None
    if file_path.suffix.lower() in ['.m4a', '.aac', '.mp4']:
        temp_wav = _convert_to_wav_for_madmom(file_path)
        if temp_wav:
            wav_path = temp_wav

    try:
        from madmom.features.downbeats import DBNDownBeatTrackingProcessor, RNNDownBeatProcessor

        # Load processors
        proc = RNNDownBeatProcessor()
        dbn = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)

        # Process audio
        activations = proc(str(wav_path))
        downbeats = dbn(activations)

        if len(downbeats) < 4:
            return "4/4", 0.5  # Default with low confidence

        # Count beats between downbeats
        beat_counts = []
        current_bar_beats = 0

        for i, (time, beat_num) in enumerate(downbeats):
            if beat_num == 1 and i > 0:
                if current_bar_beats > 0:
                    beat_counts.append(current_bar_beats)
                current_bar_beats = 1
            else:
                current_bar_beats += 1

        if not beat_counts:
            return "4/4", 0.5

        # Find most common beat count
        from collections import Counter

        count_freq = Counter(beat_counts)
        most_common_beats, frequency = count_freq.most_common(1)[0]

        # Map to time signature
        time_sig_map = {3: "3/4", 4: "4/4", 6: "6/8", 2: "2/4"}
        time_sig = time_sig_map.get(most_common_beats, f"{most_common_beats}/4")

        # Calculate confidence based on consistency
        confidence = frequency / len(beat_counts) if beat_counts else 0.5

        return time_sig, round(confidence, 3)

    except Exception as e:
        logger.warning(f"madmom time signature detection failed: {e}")
        return "4/4", 0.5
    finally:
        # Clean up temp file
        if temp_wav and temp_wav.exists():
            try:
                temp_wav.unlink()
            except Exception:
                pass


def _detect_beats_madmom(file_path: Path) -> list[float]:
    """
    Detect beat positions using madmom.

    Args:
        file_path: Path to audio file

    Returns:
        List of beat timestamps in seconds
    """
    if not MADMOM_AVAILABLE:
        return []

    # Convert to wav if needed (madmom struggles with m4a without ffmpeg)
    wav_path = file_path
    temp_wav = None
    if file_path.suffix.lower() in ['.m4a', '.aac', '.mp4']:
        temp_wav = _convert_to_wav_for_madmom(file_path)
        if temp_wav:
            wav_path = temp_wav

    try:
        from madmom.features.beats import DBNBeatTrackingProcessor, RNNBeatProcessor

        # Load processors
        proc = RNNBeatProcessor()
        dbn = DBNBeatTrackingProcessor(fps=100)

        # Process audio
        activations = proc(str(wav_path))
        beats = dbn(activations)

        # Return as list of floats
        return [round(float(b), 3) for b in beats]

    except Exception as e:
        logger.warning(f"madmom beat detection failed: {e}")
        return []
    finally:
        # Clean up temp file
        if temp_wav and temp_wav.exists():
            try:
                temp_wav.unlink()
            except Exception:
                pass


def _detect_chords_librosa(file_path: Path) -> list[ChordSegment]:
    """
    Detect chord progression using librosa's chroma features.

    This is a simpler approach than madmom's deep learning but more compatible.
    It uses chroma features and template matching for basic chord detection.

    Args:
        file_path: Path to audio file

    Returns:
        List of ChordSegment objects
    """
    try:
        # Load audio
        y, sr = librosa.load(file_path, sr=22050, mono=True)

        # Compute chroma features
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)

        # Chord templates for major and minor chords
        chord_templates = {}
        chord_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        for i, root in enumerate(chord_names):
            # Major chord template (root, major 3rd, perfect 5th)
            major = np.zeros(12)
            major[i] = 1.0
            major[(i + 4) % 12] = 0.8  # Major 3rd
            major[(i + 7) % 12] = 0.9  # Perfect 5th
            chord_templates[root] = major

            # Minor chord template
            minor = np.zeros(12)
            minor[i] = 1.0
            minor[(i + 3) % 12] = 0.8  # Minor 3rd
            minor[(i + 7) % 12] = 0.9  # Perfect 5th
            chord_templates[f'{root}m'] = minor

        # Analyze each frame and find best matching chord
        hop_duration = 512 / sr
        segments = []
        current_chord = None
        current_start = 0.0

        for frame_idx in range(chroma.shape[1]):
            frame = chroma[:, frame_idx]
            frame_time = frame_idx * hop_duration

            # Find best matching chord
            best_chord = None
            best_score = 0.3  # Minimum threshold

            for chord_name, template in chord_templates.items():
                # Cosine similarity
                score = np.dot(frame, template) / (np.linalg.norm(frame) * np.linalg.norm(template) + 1e-10)
                if score > best_score:
                    best_score = score
                    best_chord = chord_name

            # Track chord changes
            if best_chord != current_chord:
                if current_chord is not None and frame_time - current_start > 0.5:
                    # Save previous chord segment (only if longer than 0.5s)
                    segments.append(ChordSegment(
                        start=round(current_start, 3),
                        end=round(frame_time, 3),
                        chord=current_chord,
                    ))
                current_chord = best_chord
                current_start = frame_time

        # Add final segment
        if current_chord is not None:
            final_time = chroma.shape[1] * hop_duration
            if final_time - current_start > 0.5:
                segments.append(ChordSegment(
                    start=round(current_start, 3),
                    end=round(final_time, 3),
                    chord=current_chord,
                ))

        # Merge consecutive segments with same chord
        merged = []
        for seg in segments:
            if merged and merged[-1].chord == seg.chord:
                merged[-1] = ChordSegment(
                    start=merged[-1].start,
                    end=seg.end,
                    chord=seg.chord,
                )
            else:
                merged.append(seg)

        return merged

    except Exception as e:
        logger.warning(f"librosa chord detection failed: {e}")
        return []


def _detect_chords_madmom(file_path: Path) -> list[ChordSegment]:
    """
    Detect chord progression using madmom's deep chroma chord recognition.

    Falls back to librosa-based detection if madmom fails.

    Args:
        file_path: Path to audio file

    Returns:
        List of ChordSegment objects
    """
    if not MADMOM_AVAILABLE:
        return _detect_chords_librosa(file_path)

    # Convert to wav if needed (madmom struggles with m4a without ffmpeg)
    wav_path = file_path
    temp_wav = None
    if file_path.suffix.lower() in ['.m4a', '.aac', '.mp4']:
        temp_wav = _convert_to_wav_for_madmom(file_path)
        if temp_wav:
            wav_path = temp_wav

    try:
        from madmom.features.chords import DeepChromaChordRecognitionProcessor

        # Load processor
        proc = DeepChromaChordRecognitionProcessor()

        # Process audio - returns list of (start, end, chord) tuples
        chords = proc(str(wav_path))

        # Convert to ChordSegment objects
        segments = []
        for start, end, chord in chords:
            # Skip 'N' (no chord) segments
            if chord != 'N':
                segments.append(ChordSegment(
                    start=round(float(start), 3),
                    end=round(float(end), 3),
                    chord=str(chord),
                ))

        return segments

    except Exception as e:
        logger.warning(f"madmom chord detection failed: {e}, falling back to librosa")
        return _detect_chords_librosa(file_path)
    finally:
        # Clean up temp file
        if temp_wav and temp_wav.exists():
            try:
                temp_wav.unlink()
            except Exception:
                pass


def is_extended_analysis_available() -> bool:
    """Check if extended audio analysis (madmom) is available."""
    return MADMOM_AVAILABLE


def analyze_audio(file_path: Path, include_extended: bool = True) -> AudioAnalysisResult:
    """
    Analyze an audio file to detect tempo, key, and optionally time signature, chords, and beats.

    Args:
        file_path: Path to the audio file
        include_extended: Whether to include madmom-based analysis (time sig, chords, beats)
                         Only works if madmom is installed.

    Returns:
        AudioAnalysisResult with detected values
    """
    try:
        logger.info(f"Loading audio file: {file_path}")

        # Load audio file with librosa
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

        # Build result
        result = AudioAnalysisResult(
            tempo=round(tempo, 1),
            tempo_confidence=round(tempo_confidence, 3),
            key=key,
            key_confidence=round(key_confidence, 3),
            duration_seconds=round(duration, 2),
            success=True,
        )

        # Extended analysis with madmom (if available)
        if include_extended:
            if MADMOM_AVAILABLE:
                logger.info("Detecting time signature (madmom)...")
                time_sig, time_sig_confidence = _detect_time_signature_madmom(file_path)
                result.time_signature = time_sig
                result.time_signature_confidence = time_sig_confidence
                logger.info(f"Time signature: {time_sig} (confidence: {time_sig_confidence:.2f})")

                logger.info("Detecting beats (madmom)...")
                beats = _detect_beats_madmom(file_path)
                result.beat_positions = beats
                logger.info(f"Detected {len(beats)} beats")

                logger.info("Detecting chords (madmom)...")
                chords = _detect_chords_madmom(file_path)
                result.chords = chords
                logger.info(f"Detected {len(chords)} chord segments")
            else:
                logger.info("Skipping extended analysis - madmom not installed")

        return result

    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        return AudioAnalysisResult(
            success=False,
            error=str(e),
        )


def chords_to_json(chords: list[ChordSegment]) -> str:
    """Convert chord segments to JSON string for storage."""
    return json.dumps([
        {"start": c.start, "end": c.end, "chord": c.chord}
        for c in chords
    ])


def beats_to_json(beats: list[float]) -> str:
    """Convert beat positions to JSON string for storage."""
    return json.dumps(beats)


def chords_from_json(json_str: Optional[str]) -> list[ChordSegment]:
    """Parse chord segments from JSON string."""
    if not json_str:
        return []
    try:
        data = json.loads(json_str)
        return [ChordSegment(**c) for c in data]
    except Exception:
        return []


def beats_from_json(json_str: Optional[str]) -> list[float]:
    """Parse beat positions from JSON string."""
    if not json_str:
        return []
    try:
        return json.loads(json_str)
    except Exception:
        return []
