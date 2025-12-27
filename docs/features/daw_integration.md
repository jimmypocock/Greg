# DAW Integration (Ableton Live)

> **Status:** Future Vision (Phase 5+)
> **Priority:** High value, high complexity
> **Dependencies:** Multi-agent architecture, core platform stable

## Vision

Connect the AI songwriting system directly to Ableton Live, enabling real-time creative assistance while producing music.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AI SONGWRITING SYSTEM                            │
│                   (Multi-Agent Orchestrator)                         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│   Option 1    │      │   Option 2    │      │   Option 3    │
│  Companion    │      │ Max for Live  │      │  Remote       │
│ App (OSC)     │      │   Device      │      │  Scripts      │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ABLETON LIVE                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │  MIDI   │  │  Audio  │  │ Arrange │  │ Session │  │  Mixer  │   │
│  │ Tracks  │  │ Tracks  │  │  View   │  │  View   │  │         │   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Integration Approaches

### Comparison

| Approach | Complexity | Flexibility | Latency | Best For |
|----------|------------|-------------|---------|----------|
| **Companion App (OSC)** | Low | High | ~10ms | Starting point |
| **Max for Live Device** | Medium | Medium | <1ms | Tight integration |
| **Remote Script (Python)** | High | Low | <1ms | Deep control |

### Recommended Path

1. **Start:** Companion App with OSC
2. **Later:** Max for Live for embedded experience
3. **Optional:** Remote Script for power users

---

## Option 1: Companion App with OSC (Recommended Start)

The most flexible approach. Build a standalone app that communicates with Ableton via OSC protocol.

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    COMPANION APP (Electron/Tauri)                 │
│                                                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐  │
│  │   React UI      │    │  AI Orchestrator │    │ MIDI/OSC    │  │
│  │                 │◄──►│  (Your Agents)   │◄──►│ Bridge      │  │
│  │  • Lyrics pad   │    │                  │    │             │  │
│  │  • Chord suggest│    │  • Theme Agent   │    │ • Send MIDI │  │
│  │  • Structure    │    │  • Lyrics Agent  │    │ • Receive   │  │
│  │  • Chat         │    │  • Harmony Agent │    │   state     │  │
│  └─────────────────┘    └─────────────────┘    └──────────────┘  │
│                                                       │          │
└───────────────────────────────────────────────────────│──────────┘
                                                        │
                        OSC (port 11000) ◄──────────────┤
                        MIDI (virtual port) ◄───────────┤
                                                        │
┌───────────────────────────────────────────────────────│──────────┐
│                       ABLETON LIVE                    ▼          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    AbletonOSC (M4L Device)                  │ │
│  │   • Exposes Live's API over OSC                             │ │
│  │   • Read: tempo, tracks, clips, playing state               │ │
│  │   • Write: create clips, set notes, trigger scenes          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ AI Chords    │  │ AI Melody    │  │ AI Bass      │            │
│  │ (MIDI Track) │  │ (MIDI Track) │  │ (MIDI Track) │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

### Prerequisites

1. **AbletonOSC** - Max for Live device that exposes Ableton's API
   - GitHub: https://github.com/ideoforms/AbletonOSC
   - Drag onto a MIDI track, listens on port 11000

2. **python-osc** - Python OSC library
   ```bash
   uv add python-osc
   ```

---

## Python OSC Bridge

```python
# api/services/daw/ableton_bridge.py

from pythonosc import udp_client, dispatcher, osc_server
from dataclasses import dataclass, field
from typing import Callable, Optional
import threading
import asyncio


@dataclass
class AbletonState:
    """Current state read from Ableton."""
    tempo: float = 120.0
    is_playing: bool = False
    current_bar: int = 0
    current_beat: float = 0.0
    selected_track: int = 0
    tracks: list[dict] = field(default_factory=list)

    # Musical context
    detected_key: Optional[str] = None
    detected_chords: list[str] = field(default_factory=list)


class AbletonBridge:
    """
    Bidirectional communication with Ableton Live via OSC.
    """

    def __init__(
        self,
        ableton_host: str = "127.0.0.1",
        ableton_port: int = 11000,
        receive_port: int = 11001,
    ):
        # Client to send messages TO Ableton
        self.client = udp_client.SimpleUDPClient(ableton_host, ableton_port)

        # Server to receive messages FROM Ableton
        self.dispatcher = dispatcher.Dispatcher()
        self.state = AbletonState()
        self._setup_handlers()

        self.server = osc_server.ThreadingOSCUDPServer(
            ("127.0.0.1", receive_port),
            self.dispatcher,
        )

        # Callbacks for state changes
        self.on_state_change: Optional[Callable[[AbletonState], None]] = None

    def _setup_handlers(self):
        """Register OSC message handlers."""
        self.dispatcher.map("/live/song/get/tempo", self._handle_tempo)
        self.dispatcher.map("/live/song/get/is_playing", self._handle_playing)
        self.dispatcher.map("/live/song/get/current_song_time", self._handle_time)
        self.dispatcher.map("/live/clip/get/notes", self._handle_notes)

    def _handle_tempo(self, address, *args):
        self.state.tempo = args[0]
        self._notify_change()

    def _handle_playing(self, address, *args):
        self.state.is_playing = bool(args[0])
        self._notify_change()

    def _handle_time(self, address, *args):
        time_in_beats = args[0]
        self.state.current_bar = int(time_in_beats // 4)
        self.state.current_beat = time_in_beats % 4
        self._notify_change()

    def _handle_notes(self, address, *args):
        """Parse MIDI notes from a clip."""
        # AbletonOSC returns: [pitch, start, duration, velocity, mute, ...]
        notes = []
        for i in range(0, len(args), 5):
            notes.append({
                "pitch": args[i],
                "start": args[i + 1],
                "duration": args[i + 2],
                "velocity": args[i + 3],
                "mute": args[i + 4],
            })
        return notes

    def _notify_change(self):
        if self.on_state_change:
            self.on_state_change(self.state)

    def start(self):
        """Start listening for OSC messages."""
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.refresh_state()

    def refresh_state(self):
        """Request current state from Ableton."""
        self.client.send_message("/live/song/get/tempo", [])
        self.client.send_message("/live/song/get/is_playing", [])
        self.client.send_message("/live/song/get/num_tracks", [])

    # ─────────────────────────────────────────────────────────────
    # SENDING COMMANDS TO ABLETON
    # ─────────────────────────────────────────────────────────────

    def set_tempo(self, bpm: float):
        """Set the session tempo."""
        self.client.send_message("/live/song/set/tempo", [bpm])

    def create_clip(self, track: int, slot: int, length: float = 4.0):
        """Create a new empty clip."""
        self.client.send_message("/live/clip_slot/create_clip", [track, slot, length])

    def add_notes_to_clip(self, track: int, slot: int, notes: list[dict]):
        """
        Add MIDI notes to a clip.

        notes: List of dicts with keys: pitch, start, duration, velocity
        """
        # Clear existing notes
        self.client.send_message("/live/clip/remove/notes", [track, slot])

        # Add each note
        for note in notes:
            self.client.send_message("/live/clip/add/notes", [
                track,
                slot,
                note["pitch"],
                note["start"],
                note["duration"],
                note.get("velocity", 100),
                0,  # Not muted
            ])

    def fire_clip(self, track: int, slot: int):
        """Start playing a clip."""
        self.client.send_message("/live/clip/fire", [track, slot])

    def stop_track(self, track: int):
        """Stop all clips on a track."""
        self.client.send_message("/live/track/stop_all_clips", [track])
```

---

## MIDI Utilities

```python
# api/services/daw/midi_utils.py

import re
from typing import Optional


# Chord intervals
CHORD_INTERVALS = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "m": [0, 3, 7],
    "7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "m7": [0, 3, 7, 10],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus4": [0, 5, 7],
    "sus2": [0, 2, 7],
}

# Note names to MIDI pitch class
NOTE_TO_PITCH = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11,
}


def chord_to_midi_notes(
    chord: str,
    octave: int = 4,
    start: float = 0.0,
    duration: float = 4.0,
    velocity: int = 100,
) -> list[dict]:
    """
    Convert a chord symbol to MIDI note dictionaries.

    Args:
        chord: Chord symbol (e.g., "Am7", "Cmaj7", "F#min")
        octave: Base octave
        start: Start time in beats
        duration: Duration in beats
        velocity: MIDI velocity

    Returns:
        List of note dicts with pitch, start, duration, velocity
    """
    # Parse chord: "Am7" -> root="A", quality="m7"
    match = re.match(r"([A-G][#b]?)(.*)", chord)
    if not match:
        return []

    root_note, quality = match.groups()

    # Get root pitch
    root = NOTE_TO_PITCH.get(root_note[0], 0)
    if len(root_note) > 1:
        if root_note[1] == "#":
            root += 1
        elif root_note[1] == "b":
            root -= 1

    # Get intervals for chord quality
    quality = quality.lower() if quality else "maj"
    intervals = CHORD_INTERVALS.get("maj")  # Default

    for key, val in CHORD_INTERVALS.items():
        if key in quality:
            intervals = val
            break

    # Build MIDI notes
    base_pitch = root + (octave * 12)
    return [
        {
            "pitch": base_pitch + interval,
            "start": start,
            "duration": duration,
            "velocity": velocity,
        }
        for interval in intervals
    ]


def melody_to_midi_notes(
    melody_data: str,
    start_beat: float = 0.0,
    velocity: int = 100,
) -> list[dict]:
    """
    Convert melody notation to MIDI notes.

    Format: "NOTE:DURATION NOTE:DURATION ..."
    Example: "C4:1 D4:0.5 E4:0.5 G4:2"

    Returns:
        List of note dicts
    """
    notes = []
    current_beat = start_beat

    for token in melody_data.split():
        if ":" not in token:
            continue

        note_part, duration_str = token.split(":")
        duration = float(duration_str)

        # Parse note: "C4", "F#5", "Bb3"
        match = re.match(r"([A-G])([#b]?)(\d)", note_part)
        if not match:
            current_beat += duration
            continue

        note_name, accidental, octave = match.groups()
        pitch = NOTE_TO_PITCH[note_name] + (int(octave) * 12)

        if accidental == "#":
            pitch += 1
        elif accidental == "b":
            pitch -= 1

        notes.append({
            "pitch": pitch,
            "start": current_beat,
            "duration": duration,
            "velocity": velocity,
        })

        current_beat += duration

    return notes


def parse_chord_progression(
    progression: str,
    octave: int = 3,
    velocity: int = 100,
) -> tuple[list[dict], float]:
    """
    Parse AI-generated chord progression to MIDI notes.

    Input format: "Am7|4 Dm7|4 G7|2 Cmaj7|2"

    Returns:
        Tuple of (notes list, total length in beats)
    """
    all_notes = []
    current_beat = 0.0

    for token in progression.split():
        if "|" not in token:
            continue

        chord, duration_str = token.split("|")
        duration = float(duration_str)

        notes = chord_to_midi_notes(
            chord=chord,
            octave=octave,
            start=current_beat,
            duration=duration,
            velocity=velocity,
        )
        all_notes.extend(notes)
        current_beat += duration

    return all_notes, current_beat
```

---

## AI-DAW Integration Service

```python
# api/services/daw/assistant.py

import asyncio
from uuid import UUID

from api.services.daw.ableton_bridge import AbletonBridge, AbletonState
from api.services.daw.midi_utils import (
    chord_to_midi_notes,
    melody_to_midi_notes,
    parse_chord_progression,
)
from songwriting_agents import SongOrchestrator, SongContext


class AIDAWAssistant:
    """
    Real-time AI songwriting assistant integrated with Ableton.
    """

    def __init__(self):
        self.bridge = AbletonBridge()
        self.orchestrator = SongOrchestrator()
        self.context = SongContext(genre="", mood="", theme_description="")

        # Track assignments in Ableton
        self.tracks = {
            "chords": 0,   # Track 1: Chord MIDI
            "melody": 1,   # Track 2: Melody MIDI
            "bass": 2,     # Track 3: Bass MIDI
        }

        # Subscribe to Ableton state changes
        self.bridge.on_state_change = self._on_ableton_update

    def start(self):
        """Initialize connection to Ableton."""
        self.bridge.start()

    def _on_ableton_update(self, state: AbletonState):
        """Called when Ableton state changes."""
        # Could trigger AI suggestions based on playback position
        pass

    async def suggest_chord_progression(
        self,
        mood: str,
        key: str = "C",
        bars: int = 8,
    ) -> str:
        """Get AI chord suggestions."""
        self.context.mood = mood
        self.context.key = key

        result = await self.orchestrator.agents["harmony"].process(
            f"Suggest a {bars}-bar chord progression in {key} that feels {mood}. "
            f"Format: CHORD|BEATS (e.g., Am7|4 Dm7|4 G7|2 Cmaj7|2)",
            self.context,
        )

        return result

    async def send_chords_to_ableton(
        self,
        chord_string: str,
        slot: int = 0,
        octave: int = 3,
    ):
        """Parse AI-generated chords and create a clip in Ableton."""
        all_notes, total_length = parse_chord_progression(
            chord_string, octave=octave
        )

        track = self.tracks["chords"]

        self.bridge.create_clip(track, slot, total_length)
        await asyncio.sleep(0.1)  # Give Ableton time to create clip
        self.bridge.add_notes_to_clip(track, slot, all_notes)

    async def suggest_melody(
        self,
        lyrics_line: str,
        chord_context: str,
        key: str = "C",
    ) -> str:
        """Generate a melody for a lyrics line over given chords."""
        result = await self.orchestrator.agents["melody"].process(
            f"""Create a vocal melody for this lyric line:
"{lyrics_line}"

Chords: {chord_context}
Key: {key}

Output format: NOTE:DURATION (e.g., C4:1 D4:0.5 E4:0.5 G4:2)
""",
            self.context,
        )

        return result

    async def send_melody_to_ableton(
        self,
        melody_string: str,
        slot: int = 0,
    ):
        """Send AI-generated melody to Ableton."""
        notes = melody_to_midi_notes(melody_string)

        if not notes:
            return

        track = self.tracks["melody"]
        total_length = max(n["start"] + n["duration"] for n in notes)

        self.bridge.create_clip(track, slot, total_length)
        await asyncio.sleep(0.1)
        self.bridge.add_notes_to_clip(track, slot, notes)

    async def generate_section(
        self,
        section_type: str,
        theme: str,
        key: str = "C",
        bars: int = 8,
        slot: int = 0,
    ) -> dict:
        """Generate a complete section (chords + lyrics)."""
        self.context.theme_description = theme
        self.context.key = key

        # Get chords
        chords = await self.suggest_chord_progression(
            mood=f"{section_type} energy for: {theme}",
            key=key,
            bars=bars,
        )

        # Send to Ableton
        await self.send_chords_to_ableton(chords, slot=slot)

        # Get lyrics
        lyrics = await self.orchestrator.agents["lyrics"].process(
            f"Write {section_type} lyrics ({bars} bars) about: {theme}",
            self.context,
        )

        return {
            "chords": chords,
            "lyrics": lyrics,
            "section": section_type,
        }
```

---

## Backend API Endpoints

```python
# api/routes/daw.py

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

from api.services.daw.assistant import AIDAWAssistant
from api.services.daw.midi_utils import (
    chord_to_midi_notes,
    melody_to_midi_notes,
    parse_chord_progression,
)

router = APIRouter(prefix="/daw", tags=["DAW Integration"])


# Request/Response models
class ChordRequest(BaseModel):
    mood: str
    key: str = "C"
    bars: int = 8


class ChordResponse(BaseModel):
    progression: str
    midi_notes: list[dict]
    length: float


class MelodyRequest(BaseModel):
    lyrics: str
    chords: str
    key: str = "C"


class MelodyResponse(BaseModel):
    notation: str
    midi_notes: list[dict]
    length: float


# Endpoints
@router.post("/suggest-chords", response_model=ChordResponse)
async def suggest_chords(request: ChordRequest):
    """Get AI chord suggestions with MIDI data for DAW."""
    assistant = AIDAWAssistant()

    result = await assistant.suggest_chord_progression(
        mood=request.mood,
        key=request.key,
        bars=request.bars,
    )

    midi_notes, length = parse_chord_progression(result)

    return ChordResponse(
        progression=result.replace("|", " | "),
        midi_notes=midi_notes,
        length=length,
    )


@router.post("/suggest-melody", response_model=MelodyResponse)
async def suggest_melody(request: MelodyRequest):
    """Get AI melody suggestions with MIDI data for DAW."""
    assistant = AIDAWAssistant()

    result = await assistant.suggest_melody(
        lyrics_line=request.lyrics,
        chord_context=request.chords,
        key=request.key,
    )

    midi_notes = melody_to_midi_notes(result)
    length = max(n["start"] + n["duration"] for n in midi_notes) if midi_notes else 0

    return MelodyResponse(
        notation=result,
        midi_notes=midi_notes,
        length=length,
    )


@router.post("/send-to-ableton")
async def send_to_ableton(
    track: str,  # "chords", "melody", "bass"
    notes: list[dict],
    slot: int = 0,
):
    """Send MIDI notes directly to Ableton."""
    assistant = AIDAWAssistant()
    assistant.start()

    track_index = assistant.tracks.get(track, 0)
    length = max(n["start"] + n["duration"] for n in notes) if notes else 4.0

    assistant.bridge.create_clip(track_index, slot, length)
    await asyncio.sleep(0.1)
    assistant.bridge.add_notes_to_clip(track_index, slot, notes)

    return {"status": "sent", "track": track, "slot": slot}


# WebSocket for real-time communication
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time bidirectional communication with DAW companion app."""
    await websocket.accept()

    assistant = AIDAWAssistant()
    assistant.start()

    # Send state updates to client
    def on_state_change(state):
        asyncio.create_task(websocket.send_json({
            "type": "state",
            "data": {
                "tempo": state.tempo,
                "is_playing": state.is_playing,
                "bar": state.current_bar,
                "beat": state.current_beat,
            },
        }))

    assistant.bridge.on_state_change = on_state_change

    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "suggest_chords":
                result = await suggest_chords(ChordRequest(**data["params"]))
                await websocket.send_json({
                    "type": "chords",
                    "data": result.dict(),
                })

            elif data["type"] == "send_to_ableton":
                await send_to_ableton(**data["params"])
                await websocket.send_json({
                    "type": "sent",
                    "data": {"success": True},
                })

    except Exception as e:
        print(f"WebSocket error: {e}")
```

---

## Option 2: Max for Live Device

For tighter integration, build a Max for Live device with Node.js backend:

```javascript
// ai-assistant.js (runs inside Max's node.script object)
const maxAPI = require("max-api");

const AI_BACKEND_URL = "http://localhost:8000";

maxAPI.addHandler("suggest_chords", async (mood, key, bars) => {
    try {
        const response = await fetch(`${AI_BACKEND_URL}/daw/suggest-chords`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mood, key, bars }),
        });

        const data = await response.json();

        // Send chord data back to Max
        maxAPI.outlet("chords", data.progression);

        // Send MIDI notes
        for (const note of data.midi_notes) {
            maxAPI.outlet("midi", note.pitch, note.start, note.duration, note.velocity);
        }
    } catch (error) {
        maxAPI.post(`Error: ${error.message}`);
    }
});

maxAPI.addHandler("suggest_melody", async (lyrics, chords, key) => {
    try {
        const response = await fetch(`${AI_BACKEND_URL}/daw/suggest-melody`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lyrics, chords, key }),
        });

        const data = await response.json();
        maxAPI.outlet("melody", data.notation);

        for (const note of data.midi_notes) {
            maxAPI.outlet("midi", note.pitch, note.start, note.duration, note.velocity);
        }
    } catch (error) {
        maxAPI.post(`Error: ${error.message}`);
    }
});
```

---

## Option 3: Ableton Remote Script

For deepest integration, create a Python Remote Script:

```python
# AISongwriter/__init__.py
# Location: /Applications/Ableton Live/Contents/App-Resources/MIDI Remote Scripts/AISongwriter/

from ableton.v2.control_surface import ControlSurface
import threading
import http.client
import json


class AISongwriter(ControlSurface):
    """Ableton Remote Script for AI Songwriting Assistant."""

    def __init__(self, c_instance):
        super(AISongwriter, self).__init__(c_instance)
        self._song = self.song()
        self._setup_listeners()
        self.log_message("AI Songwriter initialized")

    def _setup_listeners(self):
        self._song.add_tempo_listener(self._on_tempo_change)
        self._song.add_is_playing_listener(self._on_play_state_change)

    def _on_tempo_change(self):
        self.log_message(f"Tempo: {self._song.tempo}")

    def _on_play_state_change(self):
        self.log_message(f"Playing: {self._song.is_playing}")

    def _create_clip_with_notes(self, track_idx, slot_idx, length, notes):
        """Create a clip and populate with MIDI notes."""
        try:
            track = self._song.tracks[track_idx]
            clip_slot = track.clip_slots[slot_idx]

            if not clip_slot.has_clip:
                clip_slot.create_clip(length)

            clip = clip_slot.clip
            clip.remove_notes(0, 0, length, 128)
            clip.set_notes(tuple(notes))

        except Exception as e:
            self.log_message(f"Error: {e}")

    def request_ai_chords(self, mood, key, bars):
        """Request chords from AI backend (runs in background)."""
        def _request():
            try:
                conn = http.client.HTTPConnection("localhost", 8000)
                payload = json.dumps({"mood": mood, "key": key, "bars": bars})
                headers = {"Content-Type": "application/json"}

                conn.request("POST", "/daw/suggest-chords", payload, headers)
                response = conn.getresponse()
                data = json.loads(response.read().decode())

                self.schedule_message(0, lambda: self._handle_chord_response(data))

            except Exception as e:
                self.log_message(f"Request error: {e}")

        threading.Thread(target=_request).start()

    def _handle_chord_response(self, data):
        """Process AI response and create clip."""
        notes = [
            (n["pitch"], n["start"], n["duration"], n["velocity"], False)
            for n in data.get("midi_notes", [])
        ]

        self._create_clip_with_notes(
            track_idx=0,
            slot_idx=self._find_empty_slot(0),
            length=data.get("length", 8.0),
            notes=notes,
        )

    def _find_empty_slot(self, track_idx):
        """Find first empty clip slot."""
        track = self._song.tracks[track_idx]
        for i, slot in enumerate(track.clip_slots):
            if not slot.has_clip:
                return i
        return 0

    def disconnect(self):
        self._song.remove_tempo_listener(self._on_tempo_change)
        self._song.remove_is_playing_listener(self._on_play_state_change)
        super(AISongwriter, self).disconnect()
```

---

## Companion App UI (React)

```tsx
// components/DAWAssistant.tsx

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface AbletonState {
  tempo: number;
  is_playing: boolean;
  bar: number;
  beat: number;
}

export function DAWAssistant() {
  const [mood, setMood] = useState('melancholic');
  const [key, setKey] = useState('Am');
  const [suggestions, setSuggestions] = useState<string | null>(null);
  const [abletonState, setAbletonState] = useState<AbletonState | null>(null);

  const { send, lastMessage, isConnected } = useWebSocket('ws://localhost:8000/daw/ws');

  useEffect(() => {
    if (lastMessage?.type === 'state') {
      setAbletonState(lastMessage.data);
    } else if (lastMessage?.type === 'chords') {
      setSuggestions(lastMessage.data.progression);
    }
  }, [lastMessage]);

  const handleSuggestChords = () => {
    send({
      type: 'suggest_chords',
      params: { mood, key, bars: 8 },
    });
  };

  const handleSendToAbleton = () => {
    if (!suggestions) return;
    send({
      type: 'send_to_ableton',
      params: { track: 'chords', slot: 0 },
    });
  };

  return (
    <div className="p-6 bg-gray-900 text-white">
      <header className="mb-6">
        <h1 className="text-xl font-bold">AI Songwriting Assistant</h1>
        <div className="text-sm text-gray-400">
          Ableton: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          {abletonState?.is_playing && ` | Bar ${abletonState.bar}`}
        </div>
      </header>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <select
          value={mood}
          onChange={(e) => setMood(e.target.value)}
          className="bg-gray-800 rounded p-2"
        >
          <option value="melancholic">Melancholic</option>
          <option value="uplifting">Uplifting</option>
          <option value="dark">Dark</option>
          <option value="dreamy">Dreamy</option>
        </select>

        <select
          value={key}
          onChange={(e) => setKey(e.target.value)}
          className="bg-gray-800 rounded p-2"
        >
          {['C', 'G', 'D', 'A', 'Am', 'Em', 'Dm'].map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>

        <button
          onClick={handleSuggestChords}
          className="bg-purple-600 hover:bg-purple-700 rounded p-2"
        >
          Suggest Chords
        </button>
      </div>

      {suggestions && (
        <div className="bg-gray-800 rounded p-4">
          <div className="flex justify-between mb-2">
            <span className="font-semibold">Progression</span>
            <button
              onClick={handleSendToAbleton}
              className="bg-green-600 px-3 py-1 rounded text-sm"
            >
              Send to Ableton →
            </button>
          </div>
          <div className="font-mono text-purple-300">{suggestions}</div>
        </div>
      )}
    </div>
  );
}
```

---

## Implementation Phases

| Phase | What | Effort |
|-------|------|--------|
| **1** | Backend API endpoints (`/daw/*`) | 1 week |
| **2** | OSC Bridge + AbletonOSC setup | 1 week |
| **3** | Basic companion app UI | 1-2 weeks |
| **4** | WebSocket real-time sync | 1 week |
| **5** | Polish + error handling | 1 week |
| **6** | (Optional) Max for Live device | 2-3 weeks |

---

## Dependencies

```bash
# Python
uv add python-osc

# For companion app (Electron/Tauri)
npm create tauri-app
# or
npm create electron-app
```

---

## References

- [AbletonOSC](https://github.com/ideoforms/AbletonOSC) - OSC interface for Live
- [python-osc](https://pypi.org/project/python-osc/) - Python OSC library
- [Ableton Live Object Model](https://docs.cycling74.com/max8/vignettes/live_object_model)
- [Max for Live API](https://docs.cycling74.com/max8/vignettes/live_api_overview)
- [Ableton Remote Scripts](https://remotify.io/) - Remote Script documentation
