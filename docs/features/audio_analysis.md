# Audio Analysis

> **Extract tempo, key, time signature, and chords from audio files.**

## Setup

### Install Dependencies

```bash
# Install Cython first (required for madmom)
uv pip install Cython numpy

# Install madmom without build isolation
uv pip install madmom --no-build-isolation

# Run migrations for audio fields
uv run alembic upgrade head

# Verify madmom is working
uv run python -c "import madmom; print('madmom OK')"
```

### Verify Installation

1. Start the server: `uv run greg dev`
2. Look for log message: `madmom is available - extended audio analysis enabled`
3. Upload an audio file and click "Analyze"
4. Check that time signature, chords, and beats are detected

### Files Involved

| File | Purpose |
|------|---------|
| `api/services/audio_analysis.py` | Analysis logic |
| `api/services/audio_runner.py` | Background task |
| `web/src/components/toolbox/AudioFilesPanel.tsx` | Display results |

---

## Overview

Greg can analyze audio snippets to automatically detect musical properties. All tools are open-source and run on CPU.

| Feature | Best Tool | Accuracy |
|---------|-----------|----------|
| **Tempo/BPM** | librosa or madmom | ~95%+ |
| **Key** | librosa (Krumhansl-Schmuckler) or Essentia | ~70-80% |
| **Time Signature** | madmom | ~70% |
| **Chords** | madmom or autochord | ~60-75% |
| **Beat positions** | madmom | Very high |
| **Note transcription** | Basic Pitch | Good for single instruments |

---

## Tool Ecosystem

### Tier 1: Production-Ready

| Tool | What it Does | License |
|------|--------------|---------|
| [Basic Pitch](https://github.com/spotify/basic-pitch) (Spotify) | Audio → MIDI with pitch bend. Polyphonic, instrument-agnostic, <20MB. Works on vocals. | Apache 2.0 |
| [Demucs](https://github.com/facebookresearch/demucs) (Meta) | Stem separation (vocals, drums, bass, guitar, piano). State-of-the-art. | MIT |
| [madmom](https://github.com/CPJKU/madmom) | Beat/tempo, downbeat tracking, chord recognition. Neural networks + CRFs. Academic gold standard. | BSD |
| [librosa](https://librosa.org/) | Swiss army knife. Chroma features, tempo, beat tracking, onset detection. | ISC |

### Tier 2: Specialized

| Tool | What it Does |
|------|--------------|
| [autochord](https://pypi.org/project/autochord/) | Dedicated chord recognition from audio |
| [Essentia](https://essentia.upf.edu/) | Comprehensive MIR library (C++ with Python bindings), key/chord detection |
| [aubio](https://github.com/aubio/aubio) | Real-time audio labeling (tempo, pitch, onset) |

---

## Architecture

```
Audio File (m4a/mp3/wav)
          │
          ▼
┌─────────────────────┐
│  Demucs (optional)  │  ← Isolate instruments for cleaner analysis
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│   Basic Pitch       │  ← Get MIDI/note data
│   + librosa         │  ← Get tempo, beats, key
│   + madmom          │  ← Get chords, downbeats
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  Structured Output  │
│  - Tempo: 120 BPM   │
│  - Key: C Major     │
│  - Time Sig: 4/4    │
│  - Chords: C→Am→F→G │
└─────────────────────┘
```

---

## Implementation

### Current State

madmom is already integrated for audio analysis (`api/services/audio_analysis.py`).

### Basic Example

```python
import librosa
import madmom

def analyze_audio(file_path: str) -> dict:
    # Load audio
    y, sr = librosa.load(file_path)

    # Tempo
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

    # Key detection (using chroma features)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    # Apply Krumhansl-Schmuckler algorithm for key estimation

    # Chords (using madmom)
    proc = madmom.features.chords.CNNChordFeatureProcessor()
    decode = madmom.features.chords.CRFChordRecognitionProcessor()
    chords = decode(proc(file_path))

    return {
        "tempo": float(tempo),
        "key": estimated_key,
        "chords": chords,
    }
```

### Full Analysis Service

```python
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import madmom


@dataclass
class AudioAnalysis:
    tempo: float
    key: str
    time_signature: str
    chords: list[dict]  # [{"time": 0.0, "chord": "C"}, ...]
    beats: list[float]  # Beat positions in seconds


class AudioAnalyzer:
    """Analyze audio files for musical properties."""

    def __init__(self):
        # Initialize madmom processors (heavy, do once)
        self.chord_processor = madmom.features.chords.CNNChordFeatureProcessor()
        self.chord_decoder = madmom.features.chords.CRFChordRecognitionProcessor()
        self.beat_processor = madmom.features.beats.RNNBeatProcessor()
        self.beat_decoder = madmom.features.beats.DBNBeatTrackingProcessor(fps=100)

    def analyze(self, file_path: str | Path) -> AudioAnalysis:
        file_path = str(file_path)

        # Load with librosa
        y, sr = librosa.load(file_path)

        # Tempo and beats
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beats = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # Key detection
        key = self._detect_key(y, sr)

        # Time signature (from madmom beat analysis)
        time_sig = self._detect_time_signature(file_path)

        # Chord progression
        chords = self._detect_chords(file_path)

        return AudioAnalysis(
            tempo=float(tempo),
            key=key,
            time_signature=time_sig,
            chords=chords,
            beats=beats,
        )

    def _detect_key(self, y: np.ndarray, sr: int) -> str:
        """Detect key using Krumhansl-Schmuckler algorithm."""
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_avg = np.mean(chroma, axis=1)

        # Krumhansl-Schmuckler key profiles
        major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                        2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                        2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

        keys = ['C', 'C#', 'D', 'D#', 'E', 'F',
                'F#', 'G', 'G#', 'A', 'A#', 'B']

        best_corr = -1
        best_key = 'C'
        best_mode = 'major'

        for i in range(12):
            # Rotate chroma to test each key
            rotated = np.roll(chroma_avg, -i)

            major_corr = np.corrcoef(rotated, major_profile)[0, 1]
            minor_corr = np.corrcoef(rotated, minor_profile)[0, 1]

            if major_corr > best_corr:
                best_corr = major_corr
                best_key = keys[i]
                best_mode = 'major'

            if minor_corr > best_corr:
                best_corr = minor_corr
                best_key = keys[i]
                best_mode = 'minor'

        return f"{best_key} {best_mode}"

    def _detect_time_signature(self, file_path: str) -> str:
        """Detect time signature using beat analysis."""
        # Use madmom's downbeat detection
        try:
            proc = madmom.features.downbeats.RNNDownBeatProcessor()
            decode = madmom.features.downbeats.DBNDownBeatTrackingProcessor(
                beats_per_bar=[3, 4], fps=100
            )
            result = decode(proc(file_path))

            # Count beats per bar
            if len(result) > 1:
                # Result format: [[time, beat_position], ...]
                beats_per_bar = int(max(result[:, 1]))
                return f"{beats_per_bar}/4"
        except Exception:
            pass

        return "4/4"  # Default fallback

    def _detect_chords(self, file_path: str) -> list[dict]:
        """Detect chord progression."""
        features = self.chord_processor(file_path)
        chords = self.chord_decoder(features)

        return [
            {"time": float(start), "duration": float(end - start), "chord": label}
            for start, end, label in chords
        ]
```

---

## API Endpoints

```python
from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/audio", tags=["Audio Analysis"])


@router.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    user: CurrentUser,
) -> AudioAnalysisResponse:
    """
    Analyze an audio file for tempo, key, time signature, and chords.

    Supported formats: mp3, m4a, wav, flac, ogg
    Max file size: 50MB
    Processing time: 5-30 seconds depending on length
    """
    # Save to temp file
    temp_path = await save_upload(file)

    try:
        analyzer = AudioAnalyzer()
        result = analyzer.analyze(temp_path)

        return AudioAnalysisResponse(
            tempo=result.tempo,
            key=result.key,
            time_signature=result.time_signature,
            chords=[
                ChordEvent(time=c["time"], duration=c["duration"], chord=c["chord"])
                for c in result.chords
            ],
            beats=result.beats,
        )
    finally:
        temp_path.unlink()
```

---

## Enhancement Phases

| Phase | Addition | Purpose |
|-------|----------|---------|
| **Current** | madmom + librosa | Tempo, key, basic chords |
| **Phase 2** | Improved chord detection | Better accuracy for complex progressions |
| **Phase 3** | Demucs stem separation | Analyze individual instruments from mixed tracks |
| **Phase 4** | Basic Pitch | Full MIDI transcription, note-level data |

---

## Performance

| Operation | Time (3-min song) | CPU |
|-----------|-------------------|-----|
| Tempo/beats | ~2-3 seconds | Yes |
| Key detection | ~1-2 seconds | Yes |
| Chord detection | ~10-20 seconds | Yes |
| Stem separation (Demucs) | ~30-60 seconds | Yes (GPU optional) |
| Full transcription (Basic Pitch) | ~15-30 seconds | Yes |

All operations run on CPU. GPU is optional but speeds up Demucs and Basic Pitch.

---

## Use Cases

### Auto-populate song metadata

```python
# User uploads a reference track
analysis = analyzer.analyze("reference.mp3")

song.tempo = analysis.tempo
song.key = analysis.key
song.time_signature = analysis.time_signature
```

### Match chord progression

```python
# User uploads snippet, we detect chords and convert to notation
analysis = analyzer.analyze("snippet.m4a")

# Convert to roman numeral notation relative to key
chord_structure = to_roman_numerals(analysis.chords, analysis.key)
# → "I-vi-IV-V"
```

### Guide AI suggestions

```python
# Style Library retrieval informed by detected properties
similar_songs = style_library.search(
    tempo_range=(analysis.tempo - 10, analysis.tempo + 10),
    key=analysis.key,
    chord_patterns=analysis.chord_structure,
)
```

---

## Related Documentation

- [DAW Integration](./daw_integration.md) - Send analysis results to DAW
- [Audio Generation Layer](./audio_generation.md) - Generate audio from songs
- [Songwriter Roadmap](../roadmap/SONGWRITER_ROADMAP.md) - Implementation phases
