"""Pure song matching helpers for Auto Chords."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import unquote, urlparse

_SPOTIFY_TRACK_RE = re.compile(r"spotify:track:([A-Za-z0-9]+)")


def validate_url(value: str) -> str:
    """Validate and normalize a stored chord URL."""
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("A valid http:// or https:// URL is required")
    return value


def normalize(value: str) -> str:
    """Normalize artist/title text for fallback matching."""
    value = unicodedata.normalize("NFKC", value).casefold()
    value = "".join(char if char.isalnum() else " " for char in value)
    return " ".join(value.split())


def build_match_key(artist: str, title: str) -> str:
    """Build the fallback song match key."""
    return f"{normalize(artist)}|{normalize(title)}"


def extract_spotify_track_id(content_id: object) -> str | None:
    """Extract a Spotify track ID from Sonos/Spotify media content IDs."""
    if not isinstance(content_id, str):
        return None
    decoded = unquote(content_id)
    match = _SPOTIFY_TRACK_RE.search(decoded)
    return match.group(1) if match else None


def split_summary(summary: str) -> tuple[str, str]:
    """Split the visible 'Artist – Title' registry summary."""
    summary = summary.strip()
    if "–" in summary:
        artist, title = summary.split("–", 1)
        return artist.strip(), title.strip()
    if " - " in summary:
        artist, title = summary.split(" - ", 1)
        return artist.strip(), title.strip()
    return "", summary
