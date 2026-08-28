"""Switch platform for Auto Chords."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from . import AutoChordsConfigEntry
from .const import DEFAULT_TARGET_ENABLED
from .entity import AutoChordsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutoChordsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    manager = entry.runtime_data
    entities: list[SwitchEntity] = [
        AutoChordsMasterSwitch(manager),
        AutoChordsNotificationsSwitch(manager),
        *[AutoChordsTargetSwitch(manager, target) for target in manager.notify_services],
    ]
    _remove_stale_target_entities(hass, entry, set(manager.notify_services))
    async_add_entities(entities)


def _remove_stale_target_entities(
    hass: HomeAssistant, entry: AutoChordsConfigEntry, current_targets: set[str]
) -> None:
    """Remove target switches that no longer exist in options."""
    registry = async_get_entity_registry(hass)
    prefix = f"{entry.entry_id}_notify_target_"
    for reg_entry in list(registry.entities.values()):
        if reg_entry.config_entry_id != entry.entry_id or reg_entry.domain != "switch":
            continue
        if not reg_entry.unique_id.startswith(prefix):
            continue
        target = reg_entry.unique_id.removeprefix(prefix)
        if target not in current_targets:
            registry.async_remove(reg_entry.entity_id)


class _AutoChordsSwitch(AutoChordsEntity, SwitchEntity):
    """Base switch backed by integration-owned storage."""

    _attr_entity_category = EntityCategory.CONFIG

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        """Apply and persist the requested state."""
        raise NotImplementedError


class AutoChordsMasterSwitch(_AutoChordsSwitch):
    """Master runtime switch."""

    _attr_name = None
    _attr_icon = "mdi:guitar-acoustic"

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{manager.entry.entry_id}_master"

    @property
    def is_on(self) -> bool:
        """Return whether tracking is enabled."""
        return self.manager.master_enabled

    async def _async_set_enabled(self, enabled: bool) -> None:
        await self.manager.async_set_master_enabled(enabled)


class AutoChordsNotificationsSwitch(_AutoChordsSwitch):
    """Global notification switch."""

    _attr_translation_key = "notifications"
    _attr_icon = "mdi:bell"

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{manager.entry.entry_id}_notifications"

    @property
    def is_on(self) -> bool:
        """Return whether notifications are enabled."""
        return self.manager.notifications_enabled

    async def _async_set_enabled(self, enabled: bool) -> None:
        await self.manager.async_set_notifications_enabled(enabled)


class AutoChordsTargetSwitch(_AutoChordsSwitch):
    """Enable notifications for one selected notify service."""

    _attr_translation_key = "notification_target"
    _attr_icon = "mdi:cellphone-message"

    def __init__(self, manager, target: str) -> None:
        super().__init__(manager)
        self.target = target
        self._attr_unique_id = f"{manager.entry.entry_id}_notify_target_{target}"
        target_name = target.removeprefix("mobile_app_").replace("_", " ")
        self._attr_translation_placeholders = {"target": target_name}

    @property
    def is_on(self) -> bool:
        """Return whether this target is enabled."""
        return self.manager.target_enabled.get(self.target, DEFAULT_TARGET_ENABLED)

    async def _async_set_enabled(self, enabled: bool) -> None:
        await self.manager.async_set_target_enabled(self.target, enabled)
