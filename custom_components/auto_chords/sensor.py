"""Sensor platform for Auto Chords."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AutoChordsConfigEntry
from .entity import AutoChordsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutoChordsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the current song sensor."""
    async_add_entities([AutoChordsCurrentSongSensor(entry.runtime_data)])


class AutoChordsCurrentSongSensor(AutoChordsEntity, SensorEntity):
    """Expose the most recently observed current song."""

    _attr_translation_key = "current_song"
    _attr_icon = "mdi:music-note"

    def __init__(self, manager) -> None:
        """Initialize the sensor."""
        super().__init__(manager)
        self._attr_unique_id = f"{manager.entry.entry_id}_current_song"

    @property
    def native_value(self) -> str | None:
        """Return the current song title."""
        song = self.manager.current_song
        return song.title if song else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return current song metadata."""
        song = self.manager.current_song
        if song is None:
            return {
                "artist": None,
                "source_player": None,
                "spotify_track_id": None,
                "registered": False,
                "chord_url": None,
            }
        registered = self.manager.find_registered(song)
        return {
            "artist": song.artist,
            "source_player": song.source_player,
            "spotify_track_id": song.spotify_id,
            "registered": registered is not None,
            "chord_url": registered.url if registered else None,
        }
