# Songwriter App

A songwriting assistant that helps you structure, organize, and analyze your songs.

## Features

- **Song Structure Management**: Organize songs into sections (verse, chorus, bridge, etc.) with version control
- **Chord Sheet View**: Visual chord placement above lyrics
- **Audio Analysis**: Detect tempo, key, time signature, chords, and beats from audio files
- **AI Assistance**: Structure suggestions and writing help

## Audio Analysis

The app includes audio analysis capabilities to help detect musical properties from uploaded audio files.

### Basic Analysis (always available)

Uses **librosa** to detect:
- **Tempo** (BPM) with confidence score
- **Key** (e.g., "C Major", "A Minor") with confidence score
- **Duration** in seconds

### Extended Analysis (requires madmom)

Uses **madmom** for more advanced detection:
- **Time Signature** (e.g., "4/4", "3/4", "6/8") with confidence score
- **Chord Progression** - sequence of chords with timestamps
- **Beat Positions** - precise beat timestamps in seconds

## Installing madmom (Optional)

The `madmom` library provides extended audio analysis but requires special installation due to its Cython build dependency. It cannot be installed via `uv sync` because madmom doesn't declare Cython as a build dependency in its package metadata.

### Local Development

**Important:** You must install in two steps - Cython first, then madmom.

```bash
# Step 1: Install build dependencies into your environment
uv pip install Cython numpy

# Step 2: Install madmom (now Cython is available for the build)
uv pip install madmom

# Verify installation
uv run python -c "import madmom; print('madmom installed successfully')"
```

**Why two steps?** madmom's `setup.py` imports Cython at the top level, but doesn't declare it as a build dependency in `pyproject.toml`. This means the build fails unless Cython is already installed in the environment.

### Production (Docker)

```dockerfile
# Install build dependencies first
RUN pip install Cython numpy

# Then install madmom
RUN pip install madmom

# Install the rest of your app
RUN pip install -e .
```

Or use a multi-stage build to keep the final image smaller:

```dockerfile
FROM python:3.12 AS builder

# Install build deps and madmom
RUN pip install Cython numpy
RUN pip install madmom

FROM python:3.12-slim

# Copy installed packages
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
```

### Verification

When the server starts, you'll see in the logs:
- `madmom is available - extended audio analysis enabled` if madmom is installed
- `madmom not installed - using basic audio analysis only` if not

The app works fully without madmom - you just won't get time signature, chord detection, or beat positions.

## API Endpoints

### Audio

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /songs/{id}/audio` | POST | Upload audio file |
| `GET /songs/{id}/audio` | GET | List audio files |
| `GET /songs/{id}/audio/{audio_id}` | GET | Get audio file details |
| `DELETE /songs/{id}/audio/{audio_id}` | DELETE | Delete audio file |
| `POST /songs/{id}/audio/{audio_id}/analyze` | POST | Start analysis (async) |
| `POST /songs/{id}/audio/{audio_id}/apply` | POST | Apply detected values to song |

### Analysis Response

```json
{
  "detected_tempo": 120.5,
  "confidence_tempo": 0.85,
  "detected_key": "G Major",
  "confidence_key": 0.72,
  "detected_time_signature": "4/4",
  "confidence_time_signature": 0.90,
  "detected_chords": [
    {"start": 0.0, "end": 2.5, "chord": "G"},
    {"start": 2.5, "end": 5.0, "chord": "C"},
    {"start": 5.0, "end": 7.5, "chord": "D"}
  ],
  "beat_positions": [0.5, 1.0, 1.5, 2.0, 2.5, ...],
  "duration_seconds": 180.5
}
```

Note: `detected_time_signature`, `detected_chords`, and `beat_positions` are only populated when madmom is installed.

## Database Migrations

The audio analysis features require these migrations:
- `022_add_audio_analysis_fields.py` - Adds time signature confidence, detected chords, and beat positions

Run migrations:
```bash
uv run alembic upgrade head
```
