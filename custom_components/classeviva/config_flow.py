"""Config flow for Classeviva integration."""
from __future__ import annotations

import logging
from typing import Any, Mapping

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import ClassevivaAPI
from .const import (
    CONF_CALENDAR_NAME,
    CONF_IMPORT_HISTORY,
    CONF_SCAN_INTERVAL,
    CONF_STUDENT_ID,
    CONF_STUDENT_NAME,
    DEFAULT_CALENDAR_NAME,
    DEFAULT_IMPORT_HISTORY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ClassevivaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Classeviva."""

    VERSION = 2

    def __init__(self) -> None:
        self.reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if getattr(self, "reauth_entry", None):
            defaults = self.reauth_entry.data
        else:
            defaults = {}

        if user_input is not None:
            try:
                api = ClassevivaAPI(
                    self.hass, user_input[CONF_STUDENT_ID], user_input[CONF_PASSWORD]
                )
                await api.authenticate()
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.error("Errore setup Classeviva: %s", err)
                errors["base"] = "cannot_connect"
            else:
                student_id = user_input[CONF_STUDENT_ID]
                await self.async_set_unique_id(student_id)

                if not self.reauth_entry:
                    self._abort_if_unique_id_configured()

                if self.reauth_entry:
                    self.hass.config_entries.async_update_entry(
                        self.reauth_entry, data=user_input
                    )
                    return self.async_abort(reason="reauth_successful")

                student_name = user_input.get(CONF_STUDENT_NAME, student_id)
                return self.async_create_entry(
                    title=f"Classeviva ({student_name})", data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_STUDENT_ID, default=defaults.get(CONF_STUDENT_ID, "")
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_STUDENT_NAME, default=defaults.get(CONF_STUDENT_NAME, "")
                    ): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=1440)),
                    vol.Optional(
                        CONF_CALENDAR_NAME,
                        default=defaults.get(CONF_CALENDAR_NAME, DEFAULT_CALENDAR_NAME),
                    ): str,
                    vol.Optional(
                        CONF_IMPORT_HISTORY,
                        default=defaults.get(CONF_IMPORT_HISTORY, DEFAULT_IMPORT_HISTORY),
                    ): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.FlowResult:
        entry_id = self.context.get("entry_id")
        if not entry_id:
            return self.async_abort(reason="missing_entry_id")

        self.reauth_entry = self.hass.config_entries.async_get_entry(entry_id)
        if self.reauth_entry is None:
            return self.async_abort(reason="reauth_entry_not_found")

        return await self.async_step_user()
