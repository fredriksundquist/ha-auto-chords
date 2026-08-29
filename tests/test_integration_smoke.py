"""Home Assistant fixture smoke tests for Auto Chords."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.auto_chords.const import (
    CONF_MEDIA_PLAYERS,
    CONF_NOTIFY_SERVICES,
    DOMAIN,
)


async def test_config_entry_loads_all_platforms(
    hass: HomeAssistant,
    enable_custom_integrations,
) -> None:
    """Set up a real config entry and verify device/entity platform creation."""

    async def notify_service(_call) -> None:
        return None

    hass.services.async_register("notify", "mobile_app_test", notify_service)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Auto Chords",
        data={
            CONF_MEDIA_PLAYERS: ["media_player.test"],
            CONF_NOTIFY_SERVICES: ["mobile_app_test"],
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    assert len(entities) == 7
    assert {entity.entity_id.split(".", 1)[0] for entity in entities} == {
        "button",
        "sensor",
        "switch",
        "text",
        "todo",
    }
    assert sum(entity.entity_id.startswith("switch.") for entity in entities) == 3

    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert len(devices) == 1


async def test_config_flow_rejects_empty_selections(
    hass: HomeAssistant,
    enable_custom_integrations,
) -> None:
    """The config flow must not create an inert entry with empty selections."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MEDIA_PLAYERS: [],
            CONF_NOTIFY_SERVICES: [],
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        CONF_MEDIA_PLAYERS: "media_player_required",
        CONF_NOTIFY_SERVICES: "notification_target_required",
    }
