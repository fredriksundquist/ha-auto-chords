"""Auto Chords integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, STORAGE_KEY_PREFIX, STORAGE_VERSION
from .manager import AutoChordsManager


type AutoChordsConfigEntry = ConfigEntry[AutoChordsManager]


async def async_setup_entry(hass: HomeAssistant, entry: AutoChordsConfigEntry) -> bool:
    """Set up Auto Chords from a config entry."""
    manager = AutoChordsManager(hass, entry)
    await manager.async_load()
    entry.runtime_data = manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await manager.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AutoChordsConfigEntry) -> bool:
    """Unload an Auto Chords config entry."""
    await entry.runtime_data.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: AutoChordsConfigEntry) -> None:
    """Remove integration-owned persistent data."""
    from homeassistant.helpers.storage import Store

    store: Store[dict] = Store(
        hass,
        STORAGE_VERSION,
        f"{STORAGE_KEY_PREFIX}.{entry.entry_id}",
    )
    await store.async_remove()


async def _async_update_listener(
    hass: HomeAssistant, entry: AutoChordsConfigEntry
) -> None:
    """Reload the config entry after options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)
