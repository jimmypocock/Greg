"""
Tool functions for songwriter agents.

These are plain Python functions that can be registered with PydanticAI agents.
The tools provide capabilities for analyzing lyrics, counting syllables, and
accessing song data.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.songwriter.models import Song


# Cliche patterns with suggestions
CLICHES = [
    # Love/relationship clichés
    (r"\bfall(ing)?\s+(so\s+)?hard\b", "falling hard", "Consider a more original way to express intensity of feelings"),
    (r"\bheart\s+(is\s+)?break(ing)?\b", "heart breaking", "Very common - try a fresh metaphor for emotional pain"),
    (r"\btear(s)?\s+(me|you)\s+apart\b", "tears apart", "Overused phrase for emotional damage"),
    (r"\blight\s+of\s+my\s+life\b", "light of my life", "Classic but overused endearment"),
    (r"\bcomplete(s)?\s+me\b", "completes me", "Popularized by movies, now clichéd"),
    (r"\bother\s+half\b", "other half", "Common relationship cliché"),
    (r"\bmade\s+for\s+each\s+other\b", "made for each other", "Very common romantic phrase"),
    (r"\blove\s+at\s+first\s+sight\b", "love at first sight", "Classic cliché"),
    (r"\bforever\s+and\s+(a\s+)?always\b", "forever and always", "Overused commitment phrase"),
    # Time/change clichés
    (r"\bstand\s+the\s+test\s+of\s+time\b", "stand the test of time", "Overused durability metaphor"),
    (r"\btime\s+heals\b", "time heals", "Common wisdom, not original"),
    (r"\bturn\s+back\s+time\b", "turn back time", "Very common regret expression"),
    # Emotional clichés
    (r"\bcry(ing)?\s+a\s+river\b", "crying a river", "Overused sadness metaphor"),
    (r"\bpour(ing)?\s+(my|your)\s+heart\s+out\b", "pouring heart out", "Common emotional expression"),
    (r"\bwear(ing)?\s+(my|your)\s+heart\s+on\b", "wearing heart on sleeve", "Classic vulnerability cliché"),
    (r"\bpiece(s)?\s+of\s+(my|your)\s+heart\b", "piece of heart", "Very common in songs"),
    # Journey/path clichés
    (r"\blong\s+(and\s+)?winding\s+road\b", "long winding road", "Famously used by Beatles"),
    (r"\blight\s+at\s+(the\s+)?end\b", "light at the end (of tunnel)", "Overused hope metaphor"),
    (r"\bfind\s+(my|your|our)\s+way\b", "find my/your way", "Very common journey metaphor"),
    # Sky/star clichés
    (r"\breach\s+for\s+the\s+stars\b", "reach for the stars", "Classic aspiration cliché"),
    (r"\bshoot(ing)?\s+star\b", "shooting star", "Common wish/hope symbol"),
    (r"\bmoon\s+and\s+back\b", "to the moon and back", "Extremely popular love expression"),
    # Fire/flame clichés
    (r"\bburn(ing)?\s+(with\s+)?desire\b", "burning desire", "Classic passion cliché"),
    (r"\bflame\s+(of|that)\s+never\s+dies\b", "flame that never dies", "Eternal love cliché"),
    (r"\bset\s+(my|your|the)\s+world\s+on\s+fire\b", "set the world on fire", "Overused impact metaphor"),
]


@dataclass
class ClicheResult:
    """Result from cliche detection."""
    phrase: str
    suggestion: str
    count: int


def detect_cliches(text: str) -> str:
    """
    Scan lyrics for common songwriting clichés and overused phrases.

    Args:
        text: Lyrics text (can be multiple lines)

    Returns:
        List of detected clichés with suggestions for alternatives
    """
    text_lower = text.lower()
    found_cliches: list[ClicheResult] = []

    for pattern, name, suggestion in CLICHES:
        matches = re.findall(pattern, text_lower)
        if matches:
            found_cliches.append(ClicheResult(
                phrase=name,
                suggestion=suggestion,
                count=len(matches) if isinstance(matches[0], str) else len(matches),
            ))

    if not found_cliches:
        return (
            "No common clichés detected in these lyrics. "
            "The language appears relatively fresh and original."
        )

    result = f"Found {len(found_cliches)} potential cliché(s):\n\n"
    for i, cliche in enumerate(found_cliches, 1):
        result += f"{i}. \"{cliche.phrase}\"\n"
        result += f"   → {cliche.suggestion}\n\n"

    result += (
        "Note: Clichés aren't always bad - sometimes familiar phrases connect "
        "with audiences. But consider if there's a fresher way to express the same idea."
    )
    return result


def count_syllables(text: str) -> str:
    """
    Count syllables in lyrics to check meter and rhythm.

    Args:
        text: A line or multiple lines of lyrics (separate lines with newlines)

    Returns:
        Syllable count for each line and total
    """
    lines = text.strip().split("\n")
    results = []
    total = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        count = _count_syllables_in_line(line)
        total += count
        results.append(f"  '{line}' → {count} syllables")

    output = "Syllable counts:\n" + "\n".join(results)

    if len(results) > 1:
        output += f"\n\nTotal: {total} syllables across {len(results)} lines"
        output += f"\nAverage: {total / len(results):.1f} syllables per line"

    return output


def _count_syllables_in_line(line: str) -> int:
    """Count syllables in a single line."""
    line = re.sub(r"[^\w\s]", "", line.lower())
    words = line.split()
    return sum(_count_syllables_in_word(word) for word in words)


def _count_syllables_in_word(word: str) -> int:
    """Count syllables in a word using a heuristic approach."""
    word = word.lower().strip()
    if not word:
        return 0

    # Handle common exceptions
    exceptions = {
        "the": 1, "every": 3, "different": 3, "evening": 3,
        "family": 3, "favorite": 3, "interesting": 4,
        "beautiful": 3, "business": 2, "everything": 3,
    }
    if word in exceptions:
        return exceptions[word]

    # Count vowel groups
    vowels = "aeiouy"
    count = 0
    prev_was_vowel = False

    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel

    # Adjust for common patterns
    if word.endswith("e") and count > 1:
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        count += 1
    if word.endswith("ed") and len(word) > 2 and word[-3] not in "dt":
        count -= 1

    return max(1, count)


def get_song_lyrics(song: "Song") -> str:
    """
    Get the full lyrics of the current song.

    Returns:
        Complete lyrics with section labels
    """
    lyrics = song.get_full_lyrics()
    return f"Full lyrics for '{song.title}':\n\n{lyrics}" if lyrics else "No lyrics yet."


def get_song_sections(song: "Song") -> str:
    """
    Get information about the song's sections.

    Returns:
        List of sections with line counts and previews
    """
    if not song.sections:
        return "No sections defined yet."

    result = f"Sections in '{song.title}':\n\n"
    for i, section in enumerate(song.sections):
        line_count = len(section.lines)
        preview = ""
        if section.lines:
            first_line = section.lines[0].text[:50]
            preview = f' - "{first_line}..."' if len(first_line) == 50 else f' - "{first_line}"'

        section_label = section.type.value
        if section.number:
            section_label += f" {section.number}"

        result += f"{i + 1}. [{section_label}] ({line_count} lines){preview}\n"

    return result


def get_song_metadata(song: "Song") -> str:
    """
    Get metadata about the current song.

    Returns:
        Song metadata including title, key, tempo, etc.
    """
    return (
        f"Song: {song.title}\n"
        f"Status: {song.status.value}\n"
        f"Key: {song.key or 'Not set'}\n"
        f"Tempo: {song.tempo or 'Not set'} BPM\n"
        f"Time Signature: {song.time_signature}\n"
        f"Feel: {song.feel or 'Not set'}\n"
        f"Sections: {len(song.sections)}\n"
        f"Notes: {song.notes or 'None'}"
    )


def get_song_summary(song: "Song") -> str:
    """
    Get a summary of the current song.

    Returns:
        Brief summary including section count, word count, and key info
    """
    lyrics = song.get_full_lyrics()
    word_count = len(lyrics.split()) if lyrics else 0
    section_types = [s.type.value for s in song.sections]

    return (
        f"Song Summary: '{song.title}'\n"
        f"Status: {song.status.value}\n"
        f"Sections: {len(song.sections)} ({', '.join(section_types) or 'none'})\n"
        f"Word count: {word_count}\n"
        f"Key: {song.key or 'Not set'}, "
        f"Tempo: {song.tempo or 'Not set'} BPM, "
        f"Feel: {song.feel or 'Not set'}"
    )
