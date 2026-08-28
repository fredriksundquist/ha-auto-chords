"""Config flow for Auto Chords."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import selector

from .const import CONF_MEDIA_PLAYERS, CONF_NOTIFY_SERVICES, DOMAIN


def _notify_service_options(hass) -> list[selector.SelectOptionDict]:
    """Return currently registered mobile app notify services."""
    services = hass.services.async_services().get("notify", {})
    names = sorted(name for name in services if name.startswith("mobile_app_"))
    return [
        selector.SelectOptionDict(value=name, label=f"notify.{name}") for name in names
    ]


def _schema(hass, defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the configuration schema."""
    defaults = defaults or {}
    notify_options = _notify_service_options(hass)
    valid_notify_values = {option["value"] for option in notify_options}
    default_notify = [
        value
        for value in defaults.get(CONF_NOTIFY_SERVICES, [])
        if value in valid_notify_values
    ]

    return vol.Schema(
        {
            vol.Required(
                CONF_MEDIA_PLAYERS,
                default=defaults.get(CONF_MEDIA_PLAYERS, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="media_player", multiple=True)
            ),
            vol.Required(
                CONF_NOTIFY_SERVICES,
                default=default_notify,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=notify_options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


class AutoChordsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Auto Chords."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Auto Chords", data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema(self.hass))

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow."""
        return AutoChordsOptionsFlow(config_entry)


class AutoChordsOptionsFlow(config_entries.OptionsFlow):
    """Handle Auto Chords options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self.hass, current),
        )
