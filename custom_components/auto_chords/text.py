"""Text platform for Auto Chords."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AutoChordsConfigEntry
from .entity import AutoChordsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutoChordsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up registration URL input."""
    async_add_entities([AutoChordsUrlText(entry.runtime_data)])


class AutoChordsUrlText(AutoChordsEntity, TextEntity):
    """Transient URL input used when registering the current song."""

    _attr_translation_key = "registration_url"
    _attr_icon = "mdi:link-variant"
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 255

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{manager.entry.entry_id}_registration_url"

    async def async_set_value(self, value: str) -> None:
        """Set URL input value."""
        self.manager.set_registration_url(value)

    @property
    def native_value(self) -> str:
        """Return manager-owned input value."""
        return self.manager.registration_url
