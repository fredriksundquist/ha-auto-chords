"""Base entity for Auto Chords."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_UPDATE
from .manager import AutoChordsManager


class AutoChordsEntity(Entity):
    """Base class for entities belonging to one Auto Chords device."""

    _attr_has_entity_name = True

    def __init__(self, manager: AutoChordsManager) -> None:
        """Initialize the entity."""
        self.manager = manager
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.entry.entry_id)},
            name="Auto Chords",
            manufacturer="Auto Chords",
            model="Home Assistant custom integration",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to manager updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE,
                self._async_manager_update,
            )
        )

    def _async_manager_update(self, entry_id: str) -> None:
        """Write state when this config entry changes."""
        if entry_id == self.manager.entry.entry_id:
            self.async_write_ha_state()
