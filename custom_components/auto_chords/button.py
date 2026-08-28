"""Button platform for Auto Chords."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AutoChordsConfigEntry
from .entity import AutoChordsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutoChordsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up registration button."""
    async_add_entities([AutoChordsRegisterButton(entry.runtime_data)])


class AutoChordsRegisterButton(AutoChordsEntity, ButtonEntity):
    """Register the current song with the entered URL."""

    _attr_translation_key = "register_current_song"
    _attr_icon = "mdi:playlist-plus"

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{manager.entry.entry_id}_register_current_song"

    async def async_press(self) -> None:
        """Register the current song."""
        try:
            await self.manager.async_register_current_song(
                self.manager.registration_url
            )
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
