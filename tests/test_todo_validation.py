"""Tests for to-do registry validation behavior."""

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.auto_chords.todo import _validate_chord_url


def test_todo_url_validation_converts_value_error() -> None:
    """Invalid URLs are exposed as Home Assistant errors, not raw ValueError."""
    with pytest.raises(HomeAssistantError, match="A valid http:// or https:// URL is required"):
        _validate_chord_url("https://")


def test_todo_url_validation_returns_normalized_url() -> None:
    """Valid URLs are trimmed and returned unchanged otherwise."""
    assert _validate_chord_url(" https://tabs.example/song ") == "https://tabs.example/song"
