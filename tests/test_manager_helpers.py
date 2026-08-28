"""Tests for pure Auto Chords matching helpers."""

from custom_components.auto_chords.matching import (
    build_match_key,
    extract_spotify_track_id,
    normalize,
    split_summary,
    validate_url,
)


def test_extract_spotify_track_id_from_sonos_uri() -> None:
    """Spotify IDs are extracted from URL-encoded Sonos IDs."""
    content_id = (
        "x-sonos-spotify:spotify%3atrack%3a23wea78hoXqfnOE9JciIXy"
        "?sid=9&flags=8232&sn=2"
    )
    assert extract_spotify_track_id(content_id) == "23wea78hoXqfnOE9JciIXy"


def test_extract_spotify_track_id_missing() -> None:
    """Non-Spotify content has no Spotify track ID."""
    assert extract_spotify_track_id("x-rincon-stream:RINCON") is None
    assert extract_spotify_track_id(None) is None


def test_normalize_and_match_key() -> None:
    """Fallback matching ignores case, punctuation and repeated spaces."""
    assert normalize("  Ramón!  ") == "ramón"
    assert build_match_key("Ola Bremnes", "Lofotbrev") == "ola bremnes|lofotbrev"


def test_split_summary() -> None:
    """Visible registry names split into artist and title."""
    assert split_summary("Ola Bremnes – Lofotbrev") == ("Ola Bremnes", "Lofotbrev")
    assert split_summary("Lofotbrev") == ("", "Lofotbrev")


def test_validate_url() -> None:
    """Chord URLs must be explicit HTTP(S) URLs."""
    assert validate_url(" https://tabs.example/song ") == "https://tabs.example/song"
