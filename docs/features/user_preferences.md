# User Preferences System

> **Status:** Planned
> **Priority:** Near-term
> **Purpose:** Allow users to define their songwriting style and goals so AI feedback is personalized.

## Overview

A simple preferences system that lets users tell the AI about their songwriting style, influences, and what kind of feedback they want. This context gets included in AI prompts for more relevant, personalized critiques.

## User-Facing Preferences

### Songwriting Style
- **Preferred genres** (multi-select): Pop, Rock, Country, Folk, Indie, R&B, Hip-Hop, Electronic, Jazz, Classical, Other
- **Influences** (free text): "Artists or songwriters that inspire you"
- **Typical themes** (multi-select): Love, Heartbreak, Personal growth, Social commentary, Storytelling, Abstract/poetic, Party/fun, Spiritual

### Feedback Preferences
- **Feedback style** (single select):
  - Encouraging mentor - Focus on strengths, gentle suggestions
  - Balanced critic - Mix of praise and constructive criticism
  - Tough love - Direct, honest, prioritize improvement over feelings
- **Focus areas** (multi-select): Lyrics, Melody/flow, Song structure, Chord progressions, Hook strength, Emotional impact

### Experience Level
- **Songwriting experience** (single select):
  - Beginner - New to songwriting
  - Intermediate - Written several songs
  - Experienced - Years of songwriting
  - Professional - Published/performed songwriter

### Goals
- **What are you working toward?** (free text): "I'm trying to write a full album about..." or "I want to improve my chorus hooks"

## Database Schema

```sql
-- Add to users table or create separate preferences table
ALTER TABLE users ADD COLUMN preferences JSONB DEFAULT '{}';

-- Example structure:
{
  "genres": ["indie", "folk"],
  "influences": "Phoebe Bridgers, Elliott Smith, Bon Iver",
  "themes": ["personal_growth", "heartbreak"],
  "feedback_style": "balanced",
  "focus_areas": ["lyrics", "emotional_impact"],
  "experience_level": "intermediate",
  "goals": "Working on my first EP about leaving my hometown"
}
```

## API Endpoints

```
GET  /api/preferences      - Get current user preferences
PUT  /api/preferences      - Update preferences (partial update)
```

## AI Integration

When generating feedback, include preferences in the system prompt:

```python
def build_critic_prompt(user: User, song: Song) -> str:
    prefs = user.preferences or {}

    context_parts = []

    if prefs.get("genres"):
        context_parts.append(f"Preferred genres: {', '.join(prefs['genres'])}")

    if prefs.get("influences"):
        context_parts.append(f"Musical influences: {prefs['influences']}")

    if prefs.get("feedback_style"):
        style_map = {
            "encouraging": "Be encouraging and supportive. Highlight strengths before suggestions.",
            "balanced": "Provide balanced feedback with both praise and constructive criticism.",
            "tough_love": "Be direct and honest. Prioritize actionable improvement over comfort."
        }
        context_parts.append(style_map.get(prefs["feedback_style"], ""))

    if prefs.get("experience_level"):
        context_parts.append(f"Experience level: {prefs['experience_level']}")

    if prefs.get("goals"):
        context_parts.append(f"Current goals: {prefs['goals']}")

    if prefs.get("focus_areas"):
        context_parts.append(f"Focus feedback on: {', '.join(prefs['focus_areas'])}")

    user_context = "\n".join(context_parts)

    return f"""You are a songwriting critic providing feedback.

User context:
{user_context}

Review the following song and provide feedback tailored to this user's style and goals.
"""
```

## Frontend

Add a "Preferences" tab to the Settings page with a form for each section above.

Consider adding an onboarding flow for new users to capture initial preferences.

## Future Enhancements

1. **Implicit learning** - Track which feedback users act on vs ignore
2. **Song history context** - Pull similar past songs when giving feedback
3. **Per-song overrides** - "For this song, I'm trying something different..."
4. **Genre-specific feedback models** - Different critique approaches for country vs electronic

## Implementation Steps

1. Add `preferences` JSONB column to users table (migration)
2. Create Pydantic schemas for preferences
3. Add GET/PUT endpoints
4. Build frontend preferences form in Settings
5. Update AI critic to include preferences in prompts
6. (Optional) Add onboarding flow for new users
