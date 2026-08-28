"""Switch platform for Auto Chords."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.restore_state import RestoreEntity

from . import AutoChordsConfigEntry
from .const import (
    DEFAULT_MASTER_ENABLED,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_TARGET_ENABLED,
)
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


class _RestoredAutoChordsSwitch(AutoChordsEntity, SwitchEntity, RestoreEntity):
    """Base switch with restore-state behavior."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager, default: bool) -> None:
        super().__init__(manager)
        self._attr_is_on = default

    async def async_added_to_hass(self) -> None:
        """Restore prior switch state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == STATE_ON
        self._apply_to_manager()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        self._attr_is_on = True
        self._apply_to_manager()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        self._attr_is_on = False
        self._apply_to_manager()
        self.async_write_ha_state()

    def _apply_to_manager(self) -> None:
        """Apply restored/current state to the manager."""
        raise NotImplementedError


class AutoChordsMasterSwitch(_RestoredAutoChordsSwitch):
    """Master runtime switch."""

    _attr_translation_key = "master"
    _attr_icon = "mdi:guitar-acoustic"

    def __init__(self, manager) -> None:
        super().__init__(manager, DEFAULT_MASTER_ENABLED)
        self._attr_unique_id = f"{manager.entry.entry_id}_master"

    def _apply_to_manager(self) -> None:
        self.manager.set_master_enabled(bool(self._attr_is_on))


class AutoChordsNotificationsSwitch(_RestoredAutoChordsSwitch):
    """Global notification switch."""

    _attr_translation_key = "notifications"
    _attr_icon = "mdi:bell"

    def __init__(self, manager) -> None:
        super().__init__(manager, DEFAULT_NOTIFICATIONS_ENABLED)
        self._attr_unique_id = f"{manager.entry.entry_id}_notifications"

    def _apply_to_manager(self) -> None:
        self.manager.set_notifications_enabled(bool(self._attr_is_on))


class AutoChordsTargetSwitch(_RestoredAutoChordsSwitch):
    """Enable notifications for one selected notify service."""

    _attr_icon = "mdi:cellphone-message"

    def __init__(self, manager, target: str) -> None:
        super().__init__(manager, DEFAULT_TARGET_ENABLED)
        self.target = target
        self._attr_unique_id = f"{manager.entry.entry_id}_notify_target_{target}"
        self._attr_name = f"Notify {target.removeprefix('mobile_app_').replace('_', ' ')}"

    def _apply_to_manager(self) -> None:
        self.manager.set_target_enabled(self.target, bool(self._attr_is_on))
