# Audio Generation Layer

> **Status:** Future Implementation (Phase 2-3)
> **Priority:** High (differentiating feature)
> **Dependencies:** GPU infrastructure, existing audio analysis (madmom)

## Overview

The Audio Generation Layer extends the songwriter app beyond text-based co-writing into audio ideation and demo creation. Rather than competing with full song generators like Suno or ElevenLabs, this layer focuses on **supporting the creative process** with targeted audio tools.

### Philosophy

```
┌─────────────────────────────────────────────────────────────┐
│                    SUNO / ELEVENLABS                         │
│         "Type a prompt, get a finished song"                 │
│                                                              │
│    Input: "Write me a sad country song about my dog"        │
│    Output: Complete song with vocals                         │
│                                                              │
│    → Great for consumers, not for serious songwriters        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    OUR APPROACH                              │
│      "Tools that support YOUR creative process"              │
│                                                              │
│    - Analyze reference tracks to learn from                  │
│    - Generate backing sketches to sing over                  │
│    - Get melodic ideas when stuck                            │
│    - Create quick demos to share with collaborators          │
│                                                              │
│    → You're the songwriter, AI is the assistant              │
└─────────────────────────────────────────────────────────────┘
```

### Value Proposition

| Feature | User Need | Our Solution |
|---------|-----------|--------------|
| "I want to study how my favorite songs are arranged" | Reference analysis | Stem separation (Demucs) |
| "I have lyrics but need music to sing over" | Quick instrumental | Backing track generation (MusicGen) |
| "I have chords but need melody ideas" | Melodic inspiration | MIDI melody generation |
| "I need to share a rough demo with my band" | Demo creation | ElevenLabs API integration |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AUDIO GENERATION LAYER                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      AUDIO ANALYSIS                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │ │
│  │  │   Demucs    │  │   madmom    │  │  Essentia   │             │ │
│  │  │   (stems)   │  │  (rhythm)   │  │  (features) │             │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     AUDIO GENERATION                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │ │
│  │  │  MusicGen   │  │chord2melody │  │   Magenta   │             │ │
│  │  │ (backing)   │  │   (melody)  │  │   (drums)   │             │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     EXTERNAL APIS                               │ │
│  │  ┌─────────────┐  ┌─────────────┐                              │ │
│  │  │ ElevenLabs  │  │   Suno      │  (optional, user-paid)       │ │
│  │  │   (demos)   │  │  (demos)    │                              │ │
│  │  └─────────────┘  └─────────────┘                              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         GPU WORKER                                   │
│  - Modal.com / RunPod / Lambda Labs                                 │
│  - Scales to zero when not in use                                   │
│  - 16GB+ VRAM for MusicGen                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Stem Separation (Demucs)

### Overview

[Demucs](https://github.com/facebookresearch/demucs) (Meta AI) separates audio into component stems: vocals, drums, bass, and other instruments. This helps songwriters study reference tracks and understand arrangement choices.

### Use Cases

1. **Study vocal delivery** - Isolate vocals from a reference track
2. **Analyze drum patterns** - Extract drums to understand groove
3. **Learn bass lines** - Isolate bass for transcription
4. **Understand arrangement** - See how instruments interact

### Technical Requirements

| Requirement | Specification |
|-------------|---------------|
| Model | `htdemucs` (Hybrid Transformer) |
| VRAM | 4-8 GB |
| Processing time | ~30s per minute of audio |
| Output | 4 stems: vocals, drums, bass, other |
| Quality | SDR 9.0 dB (state-of-the-art) |

### Installation

```bash
# Add to pyproject.toml
uv add demucs torch torchaudio
```

### Implementation

```python
# api/services/audio/stem_separation.py

import asyncio
import logging
import tempfile
from pathlib import Path
from uuid import UUID

import torch
import torchaudio
from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import save_audio

logger = logging.getLogger(__name__)


class StemSeparator:
    """
    Separate audio into component stems using Demucs.

    Stems:
        - vocals: Isolated vocal track
        - drums: Drum and percussion
        - bass: Bass instruments
        - other: Everything else (guitars, keys, synths)
    """

    def __init__(self, model_name: str = "htdemucs"):
        self.model_name = model_name
        self._model = None
        self._device = None

    @property
    def model(self):
        """Lazy load model to avoid memory usage when not needed."""
        if self._model is None:
            logger.info(f"Loading Demucs model: {self.model_name}")
            self._model = get_model(self.model_name)
            self._device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
            self._model.to(self._device)
        return self._model

    async def separate(
        self,
        audio_path: Path,
        output_dir: Path,
        stems: list[str] | None = None,
    ) -> dict[str, Path]:
        """
        Separate audio file into stems.

        Args:
            audio_path: Path to input audio file
            output_dir: Directory to save stems
            stems: Which stems to extract (default: all)
                   Options: ["vocals", "drums", "bass", "other"]

        Returns:
            Dictionary mapping stem name to output path
        """
        stems = stems or ["vocals", "drums", "bass", "other"]

        # Run in thread pool to not block async loop
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._separate_sync,
            audio_path,
            output_dir,
            stems,
        )

    def _separate_sync(
        self,
        audio_path: Path,
        output_dir: Path,
        stems: list[str],
    ) -> dict[str, Path]:
        """Synchronous separation (runs in thread pool)."""

        # Load audio
        wav, sr = torchaudio.load(audio_path)
        wav = wav.to(self._device)

        # Ensure stereo
        if wav.shape[0] == 1:
            wav = wav.repeat(2, 1)

        # Add batch dimension
        wav = wav.unsqueeze(0)

        # Apply model
        logger.info(f"Separating stems for: {audio_path.name}")
        with torch.no_grad():
            sources = apply_model(
                self.model,
                wav,
                device=self._device,
                progress=True,
            )

        # Save requested stems
        output_dir.mkdir(parents=True, exist_ok=True)
        stem_names = self.model.sources  # ['drums', 'bass', 'other', 'vocals']

        results = {}
        for i, name in enumerate(stem_names):
            if name in stems:
                stem_path = output_dir / f"{audio_path.stem}_{name}.wav"
                save_audio(sources[0, i], stem_path, self.model.samplerate)
                results[name] = stem_path
                logger.info(f"Saved stem: {stem_path}")

        return results

    def unload(self):
        """Unload model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            torch.cuda.empty_cache()
            logger.info("Demucs model unloaded")


# Singleton instance
_separator: StemSeparator | None = None


def get_stem_separator() -> StemSeparator:
    global _separator
    if _separator is None:
        _separator = StemSeparator()
    return _separator
```

### API Route

```python
# api/routes/audio/stems.py

import tempfile
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import FileResponse

from packages.core.auth import CurrentUser
from packages.core.jobs import JobManager
from api.services.audio.stem_separation import get_stem_separator

router = APIRouter(prefix="/audio/stems", tags=["Audio - Stems"])


class StemSeparationRequest(BaseModel):
    stems: list[str] = ["vocals", "drums", "bass", "other"]


class StemSeparationResponse(BaseModel):
    job_id: str
    status: str
    message: str


@router.post("/separate", response_model=StemSeparationResponse)
async def separate_stems(
    file: UploadFile,
    request: StemSeparationRequest,
    user: CurrentUser,
    job_manager: Annotated[JobManager, Depends(get_job_manager)],
) -> StemSeparationResponse:
    """
    Upload an audio file and separate it into stems.

    Returns a job ID for tracking progress via WebSocket.
    Processing time: ~30 seconds per minute of audio.
    """
    # Validate file type
    if not file.content_type.startswith("audio/"):
        raise HTTPException(400, "File must be an audio file")

    # Save uploaded file
    temp_dir = Path(tempfile.mkdtemp())
    input_path = temp_dir / file.filename
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Queue background job
    job = await job_manager.create_job(
        "stem_separation",
        user_id=user.id,
        input_path=str(input_path),
        output_dir=str(temp_dir / "stems"),
        stems=request.stems,
    )

    return StemSeparationResponse(
        job_id=job.id,
        status="queued",
        message=f"Separating into: {', '.join(request.stems)}",
    )


@router.get("/download/{job_id}/{stem}")
async def download_stem(
    job_id: str,
    stem: str,
    user: CurrentUser,
) -> FileResponse:
    """Download a specific stem from a completed separation job."""
    job = await get_job(job_id, user.id)

    if job.status != "completed":
        raise HTTPException(400, f"Job status: {job.status}")

    stem_path = Path(job.result["stems"][stem])
    if not stem_path.exists():
        raise HTTPException(404, f"Stem not found: {stem}")

    return FileResponse(
        stem_path,
        media_type="audio/wav",
        filename=stem_path.name,
    )
```

### Background Worker

```python
# api/jobs/audio_worker.py

from pathlib import Path

from api.services.audio.stem_separation import get_stem_separator


async def stem_separation_job(
    ctx: dict,
    input_path: str,
    output_dir: str,
    stems: list[str],
) -> dict:
    """Background job for stem separation."""
    separator = get_stem_separator()

    result = await separator.separate(
        audio_path=Path(input_path),
        output_dir=Path(output_dir),
        stems=stems,
    )

    return {
        "stems": {name: str(path) for name, path in result.items()},
        "message": f"Separated {len(result)} stems",
    }
```

---

## Component 2: Backing Track Generation (MusicGen)

### Overview

[MusicGen](https://github.com/facebookresearch/audiocraft) (Meta AI) generates instrumental music from text descriptions. This helps songwriters create quick backing tracks to sing over while developing ideas.

### Use Cases

1. **Lyric development** - Sing lyrics over a generated track
2. **Tempo/feel exploration** - Try lyrics against different grooves
3. **Demo sketching** - Create rough arrangements quickly
4. **Chord exploration** - Generate tracks with specific progressions

### Technical Requirements

| Requirement | Specification |
|-------------|---------------|
| Model | `musicgen-medium` (1.5B params) |
| VRAM | 16 GB minimum |
| Processing time | ~10s for 30s of audio |
| Output | 32kHz stereo audio |
| Duration | Up to 30s per generation |

### Installation

```bash
uv add audiocraft
```

### Implementation

```python
# api/services/audio/backing_tracks.py

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Literal

import torch
import torchaudio
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write

logger = logging.getLogger(__name__)


class BackingTrackGenerator:
    """
    Generate instrumental backing tracks using MusicGen.

    Models available:
        - small: 300M params, faster, lower quality
        - medium: 1.5B params, balanced (recommended)
        - large: 3.3B params, highest quality, slow
        - melody: 1.5B, can condition on melody input
    """

    GENRE_PROMPTS = {
        "folk": "acoustic folk with strumming guitar and soft percussion",
        "rock": "driving rock with electric guitar and drums",
        "pop": "upbeat pop with synths and modern drums",
        "country": "country with acoustic guitar, pedal steel, and brushed drums",
        "indie": "indie rock with jangly guitars and lo-fi drums",
        "r&b": "smooth r&b with rhodes piano and tight drums",
        "jazz": "jazz with piano trio, upright bass, brushed drums",
        "blues": "blues with electric guitar, organ, and shuffle drums",
        "electronic": "electronic with synthesizers and drum machine",
        "ambient": "ambient atmospheric pads and textures",
    }

    MOOD_MODIFIERS = {
        "happy": "bright, uplifting, major key",
        "sad": "melancholic, minor key, emotional",
        "energetic": "high energy, driving, powerful",
        "calm": "peaceful, gentle, relaxed",
        "dark": "moody, ominous, tense",
        "hopeful": "optimistic, building, inspiring",
        "nostalgic": "warm, vintage, wistful",
        "angry": "aggressive, intense, raw",
    }

    def __init__(self, model_size: str = "medium"):
        self.model_size = model_size
        self._model = None
        self._device = None

    @property
    def model(self):
        """Lazy load model."""
        if self._model is None:
            model_name = f"facebook/musicgen-{self.model_size}"
            logger.info(f"Loading MusicGen model: {model_name}")
            self._model = MusicGen.get_pretrained(model_name)
            self._device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
            self._model.to(self._device)
        return self._model

    def build_prompt(
        self,
        genre: str,
        mood: str | None = None,
        tempo: int | None = None,
        key: str | None = None,
        chords: list[str] | None = None,
        instruments: list[str] | None = None,
        custom_description: str | None = None,
    ) -> str:
        """
        Build a generation prompt from structured parameters.

        Args:
            genre: Musical genre (folk, rock, pop, etc.)
            mood: Emotional mood (happy, sad, energetic, etc.)
            tempo: BPM (optional)
            key: Musical key (optional, e.g., "C major", "A minor")
            chords: Chord progression (optional)
            instruments: Specific instruments to include
            custom_description: Free-form description to append

        Returns:
            Formatted prompt string
        """
        parts = []

        # Base genre prompt
        genre_lower = genre.lower()
        if genre_lower in self.GENRE_PROMPTS:
            parts.append(self.GENRE_PROMPTS[genre_lower])
        else:
            parts.append(f"{genre} instrumental")

        # Add mood modifier
        if mood:
            mood_lower = mood.lower()
            if mood_lower in self.MOOD_MODIFIERS:
                parts.append(self.MOOD_MODIFIERS[mood_lower])
            else:
                parts.append(mood)

        # Add tempo
        if tempo:
            parts.append(f"{tempo} bpm")

        # Add key
        if key:
            parts.append(f"in {key}")

        # Add chord progression hint
        if chords:
            chord_str = " - ".join(chords[:4])  # First 4 chords
            parts.append(f"chord progression: {chord_str}")

        # Add specific instruments
        if instruments:
            parts.append(f"featuring {', '.join(instruments)}")

        # Add custom description
        if custom_description:
            parts.append(custom_description)

        # Always add "instrumental, no vocals" to avoid vocal generation
        parts.append("instrumental, no vocals, backing track")

        return ", ".join(parts)

    async def generate(
        self,
        prompt: str,
        duration: float = 30.0,
        temperature: float = 1.0,
        top_k: int = 250,
        output_path: Path | None = None,
    ) -> Path:
        """
        Generate a backing track from a text prompt.

        Args:
            prompt: Text description of desired music
            duration: Length in seconds (max 30 for medium model)
            temperature: Randomness (1.0 = normal, >1 = more random)
            top_k: Top-k sampling parameter
            output_path: Where to save the audio (optional)

        Returns:
            Path to generated audio file
        """
        # Clamp duration
        duration = min(duration, 30.0)

        # Run generation in thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._generate_sync,
            prompt,
            duration,
            temperature,
            top_k,
            output_path,
        )

    def _generate_sync(
        self,
        prompt: str,
        duration: float,
        temperature: float,
        top_k: int,
        output_path: Path | None,
    ) -> Path:
        """Synchronous generation (runs in thread pool)."""

        logger.info(f"Generating backing track: {prompt[:100]}...")

        # Set generation parameters
        self.model.set_generation_params(
            duration=duration,
            temperature=temperature,
            top_k=top_k,
        )

        # Generate
        with torch.no_grad():
            wav = self.model.generate([prompt])

        # Save to file
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".wav"))

        audio_write(
            output_path.with_suffix(""),  # audio_write adds extension
            wav[0].cpu(),
            self.model.sample_rate,
            strategy="loudness",
            loudness_compressor=True,
        )

        output_path = output_path.with_suffix(".wav")
        logger.info(f"Saved backing track: {output_path}")

        return output_path

    async def generate_variations(
        self,
        prompt: str,
        count: int = 3,
        duration: float = 15.0,
    ) -> list[Path]:
        """
        Generate multiple variations of a backing track.
        Useful for exploring different interpretations.
        """
        tasks = [
            self.generate(
                prompt=prompt,
                duration=duration,
                temperature=1.0 + (i * 0.1),  # Slightly vary temperature
            )
            for i in range(count)
        ]

        return await asyncio.gather(*tasks)

    def unload(self):
        """Unload model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            torch.cuda.empty_cache()
            logger.info("MusicGen model unloaded")


# Factory
_generator: BackingTrackGenerator | None = None


def get_backing_track_generator() -> BackingTrackGenerator:
    global _generator
    if _generator is None:
        _generator = BackingTrackGenerator()
    return _generator
```

### API Route

```python
# api/routes/audio/backing_tracks.py

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from packages.core.auth import CurrentUser
from api.services.audio.backing_tracks import get_backing_track_generator

router = APIRouter(prefix="/audio/backing-tracks", tags=["Audio - Backing Tracks"])


class BackingTrackRequest(BaseModel):
    genre: str = Field(..., description="Musical genre")
    mood: str | None = Field(None, description="Emotional mood")
    tempo: int | None = Field(None, ge=40, le=200, description="BPM")
    key: str | None = Field(None, description="Musical key (e.g., 'C major')")
    chords: list[str] | None = Field(None, description="Chord progression")
    instruments: list[str] | None = Field(None, description="Specific instruments")
    custom_description: str | None = Field(None, max_length=200)
    duration: float = Field(30.0, ge=5, le=30, description="Duration in seconds")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "genre": "folk",
                    "mood": "nostalgic",
                    "tempo": 95,
                    "key": "G major",
                    "chords": ["G", "Em", "C", "D"],
                    "duration": 30,
                }
            ]
        }
    }


class BackingTrackResponse(BaseModel):
    job_id: str
    status: str
    prompt: str


@router.post("/generate", response_model=BackingTrackResponse)
async def generate_backing_track(
    request: BackingTrackRequest,
    user: CurrentUser,
    job_manager: Annotated[JobManager, Depends(get_job_manager)],
) -> BackingTrackResponse:
    """
    Generate an instrumental backing track.

    The track is generated based on genre, mood, and optional parameters.
    Returns a job ID for tracking progress.

    Processing time: ~10 seconds for 30 seconds of audio.
    """
    generator = get_backing_track_generator()

    prompt = generator.build_prompt(
        genre=request.genre,
        mood=request.mood,
        tempo=request.tempo,
        key=request.key,
        chords=request.chords,
        instruments=request.instruments,
        custom_description=request.custom_description,
    )

    job = await job_manager.create_job(
        "backing_track_generation",
        user_id=user.id,
        prompt=prompt,
        duration=request.duration,
    )

    return BackingTrackResponse(
        job_id=job.id,
        status="queued",
        prompt=prompt,
    )


@router.post("/generate-for-song/{song_id}")
async def generate_backing_for_song(
    song_id: UUID,
    user: CurrentUser,
    session: AsyncSession,
    job_manager: JobManager,
) -> BackingTrackResponse:
    """
    Generate a backing track based on a song's metadata.

    Uses the song's genre, mood, tempo, and chord information
    to automatically create an appropriate backing track.
    """
    song = await get_song_or_404(song_id, user.id, session)

    generator = get_backing_track_generator()

    prompt = generator.build_prompt(
        genre=song.metadata.get("genre", "pop"),
        mood=song.metadata.get("mood"),
        tempo=song.metadata.get("tempo"),
        key=song.metadata.get("key"),
        chords=extract_chords_from_song(song),
    )

    job = await job_manager.create_job(
        "backing_track_generation",
        user_id=user.id,
        song_id=str(song_id),
        prompt=prompt,
        duration=30.0,
    )

    return BackingTrackResponse(
        job_id=job.id,
        status="queued",
        prompt=prompt,
    )
```

### Integration with Song Editor

```typescript
// web/src/components/audio/BackingTrackPanel.tsx

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useWebSocket } from "@/hooks/useWebSocket";

interface BackingTrackPanelProps {
  song: Song;
  onTrackGenerated: (audioUrl: string) => void;
}

export function BackingTrackPanel({ song, onTrackGenerated }: BackingTrackPanelProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);

  const { subscribe } = useWebSocket();

  const generateMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/audio/backing-tracks/generate-for-song/${song.id}`);
      return response.data;
    },
    onSuccess: (data) => {
      setIsGenerating(true);

      // Subscribe to job progress
      subscribe(`job:${data.job_id}`, (event) => {
        if (event.type === "progress") {
          setProgress(event.progress);
        } else if (event.type === "completed") {
          setIsGenerating(false);
          onTrackGenerated(event.result.audio_url);
        } else if (event.type === "failed") {
          setIsGenerating(false);
          toast.error("Failed to generate backing track");
        }
      });
    },
  });

  return (
    <div className="backing-track-panel">
      <h3>Backing Track</h3>

      <div className="song-info">
        <span>Genre: {song.metadata.genre || "Not set"}</span>
        <span>Tempo: {song.metadata.tempo || "Auto"} BPM</span>
        <span>Key: {song.metadata.key || "Auto"}</span>
      </div>

      <button
        onClick={() => generateMutation.mutate()}
        disabled={isGenerating}
      >
        {isGenerating ? (
          <>Generating... {Math.round(progress * 100)}%</>
        ) : (
          <>Generate Backing Track</>
        )}
      </button>

      <p className="hint">
        Creates a 30-second instrumental based on your song's settings.
        Perfect for singing over while developing lyrics.
      </p>
    </div>
  );
}
```

---

## Component 3: Melody Generation

### Overview

Generate MIDI melodies from chord progressions to help songwriters explore melodic ideas. Uses [chord2melody](https://github.com/tanreinama/chord2melody) for chord-conditioned generation.

### Use Cases

1. **Writer's block** - Get melodic starting points
2. **Explore variations** - Generate multiple melody options
3. **Learn from suggestions** - See how AI approaches melody over chords
4. **Quick sketching** - Export MIDI to DAW for further development

### Implementation

```python
# api/services/audio/melody_generation.py

import asyncio
import logging
from pathlib import Path
from typing import Literal

from midiutil import MIDIFile

logger = logging.getLogger(__name__)


class MelodyGenerator:
    """
    Generate MIDI melodies from chord progressions.

    Approaches:
        1. Rule-based: Use music theory (chord tones, passing tones)
        2. ML-based: Use chord2melody or Magenta
        3. Hybrid: ML suggestions refined by rules
    """

    # Chord to scale degree mapping
    CHORD_TONES = {
        "maj": [0, 4, 7],      # Root, 3rd, 5th
        "min": [0, 3, 7],
        "7": [0, 4, 7, 10],
        "maj7": [0, 4, 7, 11],
        "min7": [0, 3, 7, 10],
        "dim": [0, 3, 6],
        "aug": [0, 4, 8],
    }

    # Note name to MIDI number (middle octave)
    NOTE_TO_MIDI = {
        "C": 60, "C#": 61, "Db": 61,
        "D": 62, "D#": 63, "Eb": 63,
        "E": 64,
        "F": 65, "F#": 66, "Gb": 66,
        "G": 67, "G#": 68, "Ab": 68,
        "A": 69, "A#": 70, "Bb": 70,
        "B": 71,
    }

    def parse_chord(self, chord: str) -> tuple[int, list[int]]:
        """
        Parse chord symbol into root note and intervals.

        Args:
            chord: Chord symbol (e.g., "Am", "G7", "Fmaj7")

        Returns:
            Tuple of (root_midi_note, intervals)
        """
        chord = chord.strip()

        # Extract root note
        if len(chord) > 1 and chord[1] in "#b":
            root = chord[:2]
            quality = chord[2:] or "maj"
        else:
            root = chord[0]
            quality = chord[1:] or "maj"

        root_midi = self.NOTE_TO_MIDI.get(root, 60)

        # Determine chord quality
        if "m7" in quality or "min7" in quality:
            intervals = self.CHORD_TONES["min7"]
        elif "maj7" in quality:
            intervals = self.CHORD_TONES["maj7"]
        elif "7" in quality:
            intervals = self.CHORD_TONES["7"]
        elif "dim" in quality:
            intervals = self.CHORD_TONES["dim"]
        elif "aug" in quality:
            intervals = self.CHORD_TONES["aug"]
        elif "m" in quality or "min" in quality:
            intervals = self.CHORD_TONES["min"]
        else:
            intervals = self.CHORD_TONES["maj"]

        return root_midi, intervals

    async def generate_melody(
        self,
        chords: list[str],
        beats_per_chord: int = 4,
        tempo: int = 120,
        style: Literal["simple", "flowing", "rhythmic"] = "simple",
        octave: int = 5,
    ) -> bytes:
        """
        Generate a MIDI melody over a chord progression.

        Args:
            chords: List of chord symbols
            beats_per_chord: How many beats per chord
            tempo: BPM
            style: Melodic style
            octave: Base octave (4 = middle C area)

        Returns:
            MIDI file as bytes
        """
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._generate_sync,
            chords,
            beats_per_chord,
            tempo,
            style,
            octave,
        )

    def _generate_sync(
        self,
        chords: list[str],
        beats_per_chord: int,
        tempo: int,
        style: str,
        octave: int,
    ) -> bytes:
        """Synchronous melody generation."""
        import random

        midi = MIDIFile(1)  # One track
        track = 0
        channel = 0
        time = 0
        volume = 100

        midi.addTempo(track, 0, tempo)
        midi.addProgramChange(track, channel, 0, 0)  # Piano

        octave_offset = (octave - 5) * 12

        for chord in chords:
            root, intervals = self.parse_chord(chord)
            root += octave_offset

            # Generate notes for this chord
            if style == "simple":
                notes = self._simple_melody(root, intervals, beats_per_chord)
            elif style == "flowing":
                notes = self._flowing_melody(root, intervals, beats_per_chord)
            else:  # rhythmic
                notes = self._rhythmic_melody(root, intervals, beats_per_chord)

            for note, duration in notes:
                if note is not None:  # None = rest
                    midi.addNote(track, channel, note, time, duration, volume)
                time += duration

        # Write to bytes
        from io import BytesIO
        buffer = BytesIO()
        midi.writeFile(buffer)
        buffer.seek(0)
        return buffer.read()

    def _simple_melody(
        self,
        root: int,
        intervals: list[int],
        beats: int,
    ) -> list[tuple[int | None, float]]:
        """Simple melody: one note per beat, chord tones only."""
        import random

        notes = []
        for _ in range(beats):
            interval = random.choice(intervals)
            note = root + interval
            notes.append((note, 1.0))

        return notes

    def _flowing_melody(
        self,
        root: int,
        intervals: list[int],
        beats: int,
    ) -> list[tuple[int | None, float]]:
        """Flowing melody: mix of quarter and eighth notes."""
        import random

        notes = []
        time_remaining = float(beats)
        last_note = root + intervals[0]

        while time_remaining > 0:
            # Choose duration
            if time_remaining >= 1.0:
                duration = random.choice([0.5, 0.5, 1.0])
            else:
                duration = time_remaining

            # Choose note (prefer stepwise motion)
            interval = random.choice(intervals)
            note = root + interval

            # 50% chance to approach by step
            if random.random() > 0.5 and abs(note - last_note) > 2:
                note = last_note + random.choice([-1, 1, -2, 2])

            notes.append((note, duration))
            last_note = note
            time_remaining -= duration

        return notes

    def _rhythmic_melody(
        self,
        root: int,
        intervals: list[int],
        beats: int,
    ) -> list[tuple[int | None, float]]:
        """Rhythmic melody: syncopation and rests."""
        import random

        notes = []
        time_remaining = float(beats)

        # Common rhythmic patterns (in eighth notes)
        patterns = [
            [1, 1, 1, 1],  # Even eighths
            [1.5, 0.5, 1, 1],  # Dotted
            [1, 0.5, 0.5, 1, 1],  # Syncopated
            [2, 1, 1],  # Long-short-short
        ]

        while time_remaining > 0:
            pattern = random.choice(patterns)

            for duration in pattern:
                duration = duration * 0.5  # Convert to beats
                if time_remaining <= 0:
                    break

                duration = min(duration, time_remaining)

                # Occasional rest
                if random.random() < 0.15:
                    notes.append((None, duration))
                else:
                    interval = random.choice(intervals)
                    notes.append((root + interval, duration))

                time_remaining -= duration

        return notes


# Singleton
_melody_generator: MelodyGenerator | None = None


def get_melody_generator() -> MelodyGenerator:
    global _melody_generator
    if _melody_generator is None:
        _melody_generator = MelodyGenerator()
    return _melody_generator
```

### API Route

```python
# api/routes/audio/melody.py

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/audio/melody", tags=["Audio - Melody"])


class MelodyRequest(BaseModel):
    chords: list[str] = Field(..., min_length=1, max_length=16)
    beats_per_chord: int = Field(4, ge=1, le=8)
    tempo: int = Field(120, ge=40, le=200)
    style: Literal["simple", "flowing", "rhythmic"] = "simple"
    octave: int = Field(5, ge=3, le=7)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "chords": ["Am", "F", "C", "G"],
                    "beats_per_chord": 4,
                    "tempo": 95,
                    "style": "flowing",
                }
            ]
        }
    }


@router.post("/generate")
async def generate_melody(
    request: MelodyRequest,
    user: CurrentUser,
) -> Response:
    """
    Generate a MIDI melody over a chord progression.

    Returns a MIDI file that can be imported into any DAW.
    """
    generator = get_melody_generator()

    midi_bytes = await generator.generate_melody(
        chords=request.chords,
        beats_per_chord=request.beats_per_chord,
        tempo=request.tempo,
        style=request.style,
        octave=request.octave,
    )

    filename = f"melody_{'_'.join(request.chords[:4])}.mid"

    return Response(
        content=midi_bytes,
        media_type="audio/midi",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.post("/generate-for-section/{song_id}/{section_id}")
async def generate_melody_for_section(
    song_id: UUID,
    section_id: UUID,
    style: Literal["simple", "flowing", "rhythmic"] = "simple",
    user: CurrentUser,
    session: AsyncSession,
) -> Response:
    """
    Generate a melody for a specific song section.

    Uses the section's chord progression and song tempo.
    """
    song = await get_song_or_404(song_id, user.id, session)
    section = get_section_or_404(song, section_id)

    chords = extract_section_chords(section)
    if not chords:
        raise HTTPException(400, "Section has no chord progression")

    generator = get_melody_generator()

    midi_bytes = await generator.generate_melody(
        chords=chords,
        beats_per_chord=4,
        tempo=song.metadata.get("tempo", 120),
        style=style,
    )

    filename = f"{song.title}_{section.name}_melody.mid"

    return Response(
        content=midi_bytes,
        media_type="audio/midi",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
```

---

## Component 4: External Demo Generation (ElevenLabs)

### Overview

For users who want high-quality demos with vocals, integrate ElevenLabs Music API as a premium feature. Users pay per-minute, cost passed through.

### Use Cases

1. **Share with collaborators** - "Here's a rough demo of my song idea"
2. **Pitch to publishers** - Quick professional-sounding demos
3. **Social media** - Share song snippets
4. **Validate ideas** - Hear how lyrics sound sung

### Pricing Model

| Tier | Cost | Who Pays |
|------|------|----------|
| ElevenLabs | $0.50/minute | Passed to user |
| Our margin | $0.10/minute | Platform fee |
| **User cost** | **$0.60/minute** | User |

### Implementation

```python
# api/services/audio/demo_generation.py

import logging
from uuid import UUID

import httpx
from pydantic import BaseModel

from packages.core.config import settings
from packages.core.billing import BillingService

logger = logging.getLogger(__name__)


class DemoGenerationResult(BaseModel):
    audio_url: str
    duration_seconds: float
    cost_cents: int
    stems: dict[str, str] | None = None


class DemoGenerationError(Exception):
    pass


class ElevenLabsDemoGenerator:
    """
    Generate full demos with vocals using ElevenLabs Music API.

    This is a premium feature - users are charged per minute.
    """

    BASE_URL = "https://api.elevenlabs.io/v1"
    COST_PER_MINUTE_CENTS = 60  # $0.50 ElevenLabs + $0.10 margin

    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.billing = BillingService()

    async def check_credits(self, user_id: UUID, duration_seconds: float) -> bool:
        """Check if user has enough credits for generation."""
        cost_cents = self._calculate_cost(duration_seconds)
        return await self.billing.has_credits(user_id, cost_cents)

    def _calculate_cost(self, duration_seconds: float) -> int:
        """Calculate cost in cents for a given duration."""
        minutes = duration_seconds / 60
        return int(minutes * self.COST_PER_MINUTE_CENTS)

    async def generate_demo(
        self,
        user_id: UUID,
        lyrics: str,
        style_prompt: str,
        duration_seconds: float = 60.0,
        include_stems: bool = False,
    ) -> DemoGenerationResult:
        """
        Generate a demo song with vocals.

        Args:
            user_id: User requesting generation
            lyrics: Song lyrics
            style_prompt: Description of desired style
            duration_seconds: Target duration (billed amount)
            include_stems: Whether to request stem separation

        Returns:
            DemoGenerationResult with audio URL and cost

        Raises:
            DemoGenerationError: If generation fails
        """
        # Check credits first
        cost_cents = self._calculate_cost(duration_seconds)

        if not await self.check_credits(user_id, duration_seconds):
            raise DemoGenerationError(
                f"Insufficient credits. Need ${cost_cents/100:.2f}"
            )

        # Reserve credits
        reservation = await self.billing.reserve_credits(user_id, cost_cents)

        try:
            # Call ElevenLabs API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/music/generate",
                    headers={"xi-api-key": self.api_key},
                    json={
                        "lyrics": lyrics,
                        "prompt": style_prompt,
                        "duration": duration_seconds,
                    },
                    timeout=120.0,  # Generation can take time
                )

                if response.status_code != 200:
                    raise DemoGenerationError(
                        f"ElevenLabs API error: {response.text}"
                    )

                result = response.json()

            # Confirm credit charge
            await self.billing.confirm_charge(reservation)

            # Get stems if requested
            stems = None
            if include_stems:
                stems = await self._get_stems(result["generation_id"])

            return DemoGenerationResult(
                audio_url=result["audio_url"],
                duration_seconds=result["duration"],
                cost_cents=cost_cents,
                stems=stems,
            )

        except Exception as e:
            # Release reserved credits on failure
            await self.billing.release_reservation(reservation)
            raise DemoGenerationError(str(e))

    async def _get_stems(self, generation_id: str) -> dict[str, str]:
        """Get separated stems for a generated song."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/music/{generation_id}/stems",
                headers={"xi-api-key": self.api_key},
            )

            if response.status_code == 200:
                return response.json()

            return {}


# Factory
def get_demo_generator() -> ElevenLabsDemoGenerator:
    return ElevenLabsDemoGenerator()
```

### API Route

```python
# api/routes/audio/demos.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/audio/demos", tags=["Audio - Demos"])


class DemoRequest(BaseModel):
    lyrics: str = Field(..., min_length=10, max_length=5000)
    style_prompt: str = Field(..., min_length=10, max_length=500)
    duration_seconds: float = Field(60.0, ge=15, le=180)
    include_stems: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "lyrics": "[Verse 1]\nWalking down this empty road...",
                    "style_prompt": "Indie folk, acoustic guitar, female vocals, melancholic",
                    "duration_seconds": 60,
                }
            ]
        }
    }


class DemoCostEstimate(BaseModel):
    duration_seconds: float
    cost_cents: int
    cost_display: str
    has_sufficient_credits: bool


@router.post("/estimate")
async def estimate_demo_cost(
    request: DemoRequest,
    user: CurrentUser,
) -> DemoCostEstimate:
    """
    Get cost estimate for demo generation.

    Use this before generating to show user the cost.
    """
    generator = get_demo_generator()
    cost_cents = generator._calculate_cost(request.duration_seconds)
    has_credits = await generator.check_credits(user.id, request.duration_seconds)

    return DemoCostEstimate(
        duration_seconds=request.duration_seconds,
        cost_cents=cost_cents,
        cost_display=f"${cost_cents/100:.2f}",
        has_sufficient_credits=has_credits,
    )


@router.post("/generate")
async def generate_demo(
    request: DemoRequest,
    user: CurrentUser,
    job_manager: JobManager,
) -> dict:
    """
    Generate a full demo with vocals.

    This is a premium feature. Cost: $0.60/minute.
    User must have sufficient credits.

    Returns a job ID for tracking progress.
    """
    generator = get_demo_generator()

    # Check credits
    if not await generator.check_credits(user.id, request.duration_seconds):
        raise HTTPException(
            402,
            "Insufficient credits for demo generation"
        )

    job = await job_manager.create_job(
        "demo_generation",
        user_id=user.id,
        lyrics=request.lyrics,
        style_prompt=request.style_prompt,
        duration_seconds=request.duration_seconds,
        include_stems=request.include_stems,
    )

    return {
        "job_id": job.id,
        "status": "queued",
        "estimated_cost": f"${generator._calculate_cost(request.duration_seconds)/100:.2f}",
    }


@router.post("/generate-from-song/{song_id}")
async def generate_demo_from_song(
    song_id: UUID,
    style_prompt: str,
    include_stems: bool = False,
    user: CurrentUser,
    session: AsyncSession,
) -> dict:
    """
    Generate a demo from an existing song.

    Extracts lyrics from the song and uses provided style prompt.
    """
    song = await get_song_or_404(song_id, user.id, session)

    lyrics = format_song_lyrics_for_demo(song)
    if not lyrics or len(lyrics) < 10:
        raise HTTPException(400, "Song has insufficient lyrics for demo")

    # Estimate duration from lyrics (rough: 2 seconds per word)
    word_count = len(lyrics.split())
    estimated_duration = min(max(word_count * 2, 30), 180)

    generator = get_demo_generator()

    if not await generator.check_credits(user.id, estimated_duration):
        raise HTTPException(402, "Insufficient credits")

    job = await job_manager.create_job(
        "demo_generation",
        user_id=user.id,
        song_id=str(song_id),
        lyrics=lyrics,
        style_prompt=style_prompt,
        duration_seconds=estimated_duration,
        include_stems=include_stems,
    )

    return {
        "job_id": job.id,
        "status": "queued",
        "estimated_duration": estimated_duration,
        "estimated_cost": f"${generator._calculate_cost(estimated_duration)/100:.2f}",
    }
```

---

## GPU Infrastructure

### Option 1: Modal.com (Recommended for Start)

Serverless GPU that scales to zero. Pay only for compute time.

```python
# api/services/audio/modal_runner.py

import modal

# Define the Modal app
app = modal.App("songwriter-audio")

# Image with all audio dependencies
audio_image = (
    modal.Image.debian_slim()
    .pip_install(
        "torch",
        "torchaudio",
        "demucs",
        "audiocraft",
    )
    .run_commands("apt-get update && apt-get install -y ffmpeg")
)


@app.function(
    image=audio_image,
    gpu="T4",  # Cheapest GPU, sufficient for most tasks
    timeout=300,
)
def separate_stems_modal(audio_bytes: bytes) -> dict[str, bytes]:
    """Run stem separation on Modal GPU."""
    import tempfile
    from pathlib import Path
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    import torchaudio

    # Save input
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        input_path = Path(f.name)

    # Load model and process
    model = get_model("htdemucs")
    wav, sr = torchaudio.load(input_path)
    sources = apply_model(model, wav.unsqueeze(0))

    # Return stems as bytes
    results = {}
    for i, name in enumerate(model.sources):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            torchaudio.save(f.name, sources[0, i], sr)
            results[name] = Path(f.name).read_bytes()

    return results


@app.function(
    image=audio_image,
    gpu="A10G",  # More VRAM for MusicGen
    timeout=120,
)
def generate_backing_track_modal(prompt: str, duration: float) -> bytes:
    """Run MusicGen on Modal GPU."""
    import tempfile
    from audiocraft.models import MusicGen
    from audiocraft.data.audio import audio_write

    model = MusicGen.get_pretrained("facebook/musicgen-medium")
    model.set_generation_params(duration=duration)

    wav = model.generate([prompt])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        audio_write(f.name.replace(".wav", ""), wav[0].cpu(), model.sample_rate)
        return Path(f.name).read_bytes()
```

### Cost Comparison

| Provider | GPU | Cost/Hour | Stem Sep (1 song) | Backing Track (30s) |
|----------|-----|-----------|-------------------|---------------------|
| Modal.com | T4 | $0.59 | ~$0.01 | N/A |
| Modal.com | A10G | $1.10 | ~$0.02 | ~$0.03 |
| RunPod | A4000 | $0.44 | ~$0.01 | ~$0.02 |
| Lambda Labs | A10 | $0.60 | ~$0.01 | ~$0.02 |
| Self-hosted | RTX 4090 | ~$0.15* | ~$0.002 | ~$0.005 |

*Self-hosted assumes amortized hardware cost

### Scaling Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 1: MVP                             │
│  Modal.com with scale-to-zero                               │
│  - No infrastructure management                              │
│  - Pay per use (~$0.03/request)                             │
│  - Good for < 1000 requests/day                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 2: GROWTH                          │
│  Dedicated GPU instances (RunPod/Lambda)                    │
│  - Better cost at scale                                      │
│  - Predictable performance                                   │
│  - Good for 1000-10000 requests/day                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 3: SCALE                           │
│  Self-hosted GPU cluster                                    │
│  - Lowest cost at high volume                               │
│  - Full control                                              │
│  - Good for > 10000 requests/day                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Audio generation jobs
CREATE TABLE audio_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    song_id UUID REFERENCES songs(id) ON DELETE SET NULL,

    job_type VARCHAR(50) NOT NULL,  -- 'stem_separation', 'backing_track', 'demo'
    status VARCHAR(20) NOT NULL DEFAULT 'queued',

    -- Input
    input_params JSONB NOT NULL DEFAULT '{}',

    -- Output
    output_urls JSONB,  -- {"vocals": "s3://...", "drums": "s3://..."}

    -- Cost tracking
    cost_cents INTEGER,
    gpu_seconds FLOAT,

    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

CREATE INDEX audio_jobs_user_idx ON audio_jobs(user_id);
CREATE INDEX audio_jobs_status_idx ON audio_jobs(status);

-- Generated audio files
CREATE TABLE audio_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    song_id UUID REFERENCES songs(id) ON DELETE SET NULL,
    job_id UUID REFERENCES audio_jobs(id) ON DELETE SET NULL,

    file_type VARCHAR(50) NOT NULL,  -- 'stem', 'backing_track', 'demo', 'melody'
    file_name VARCHAR(255) NOT NULL,

    -- Storage
    storage_url TEXT NOT NULL,
    file_size_bytes BIGINT,
    duration_seconds FLOAT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ  -- For temporary files
);

CREATE INDEX audio_files_user_idx ON audio_files(user_id);
CREATE INDEX audio_files_song_idx ON audio_files(song_id);
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Basic stem separation working

- [ ] Set up Modal.com account and deploy stem separation
- [ ] Create `audio_jobs` table and migration
- [ ] Implement `StemSeparator` service
- [ ] Create `/audio/stems/separate` endpoint
- [ ] Add job progress via WebSocket
- [ ] Basic UI for uploading and downloading stems

**Deliverable:** Users can upload a song and get separated stems

### Phase 2: Backing Tracks (Week 3-4)

**Goal:** Generate instrumental backing tracks

- [ ] Deploy MusicGen to Modal.com
- [ ] Implement `BackingTrackGenerator` service
- [ ] Create genre/mood prompt builder
- [ ] Create `/audio/backing-tracks/generate` endpoint
- [ ] Add "Generate Backing Track" to song editor
- [ ] Integrate with song metadata (key, tempo, chords)

**Deliverable:** Users can generate backing tracks from song settings

### Phase 3: Melody Generation (Week 5)

**Goal:** MIDI melody suggestions

- [ ] Implement `MelodyGenerator` with rule-based approach
- [ ] Create `/audio/melody/generate` endpoint
- [ ] Add melody download button to chord editor
- [ ] (Optional) Integrate chord2melody for ML-based generation

**Deliverable:** Users can get MIDI melody ideas for their chord progressions

### Phase 4: Demo Generation (Week 6-7)

**Goal:** Full demo creation via ElevenLabs

- [ ] Integrate ElevenLabs Music API
- [ ] Implement credit checking and billing
- [ ] Create `/audio/demos/generate` endpoint
- [ ] Add cost estimation UI
- [ ] Build "Create Demo" flow in song editor

**Deliverable:** Users can generate full demos with vocals (paid feature)

### Phase 5: Polish (Week 8)

**Goal:** Production readiness

- [ ] Audio file storage cleanup (expire old files)
- [ ] Usage analytics and cost tracking
- [ ] Error handling and retry logic
- [ ] Performance optimization
- [ ] Documentation

---

## Cost Projections

### Per-User Costs

| Feature | Avg Uses/Month | Cost/Use | Monthly Cost |
|---------|----------------|----------|--------------|
| Stem separation | 5 | $0.02 | $0.10 |
| Backing tracks | 10 | $0.03 | $0.30 |
| Melody generation | 20 | $0.001 | $0.02 |
| Demo generation | 2 | $6.00* | $12.00* |

*Demo generation passed to user, not platform cost

### Platform Costs at Scale

| Users | Stems | Backing | Melody | Total/Month |
|-------|-------|---------|--------|-------------|
| 100 | $10 | $30 | $2 | ~$42 |
| 1,000 | $100 | $300 | $20 | ~$420 |
| 10,000 | $1,000 | $3,000 | $200 | ~$4,200 |

**Note:** Demo generation is pass-through billing, not included in platform costs.

---

## Security Considerations

### Content Filtering

```python
# Prevent misuse of generation features
PROHIBITED_PATTERNS = [
    r"sound like .* (artist name)",
    r"cover of",
    r"remix of",
    r"in the style of .* (specific artist)",
]

async def validate_generation_request(prompt: str) -> bool:
    """Check for prohibited content in generation prompts."""
    prompt_lower = prompt.lower()

    for pattern in PROHIBITED_PATTERNS:
        if re.search(pattern, prompt_lower):
            raise HTTPException(
                400,
                "Cannot generate content that imitates specific artists"
            )

    return True
```

### Rate Limiting

```python
# Prevent abuse of GPU resources
@limiter.limit("10/hour")  # Stem separation
@limiter.limit("20/hour")  # Backing tracks
@limiter.limit("5/hour")   # Demo generation
```

### File Storage

- Audio files stored in S3 with signed URLs
- User files isolated by user_id prefix
- Automatic expiration for temporary files (7 days)
- No public access to generation outputs

---

## References

- [Meta AudioCraft](https://github.com/facebookresearch/audiocraft)
- [Demucs](https://github.com/facebookresearch/demucs)
- [ElevenLabs Music API](https://elevenlabs.io/docs/api-reference/music)
- [Modal.com GPU](https://modal.com/docs/guide/gpu)
- [chord2melody](https://github.com/tanreinama/chord2melody)
- [Magenta](https://magenta.tensorflow.org/)
- [State of AI Music 2025](https://www.billboard.com/lists/biggest-ai-music-stories-2025-suno-udio-charts-more/)
