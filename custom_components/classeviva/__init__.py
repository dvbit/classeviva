"""The Classeviva Registro Elettronico integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import entity_registry as er

from .api import ClassevivaAPI
from .const import (
    CONF_CALENDAR_NAME,
    CONF_SCAN_INTERVAL,
    CONF_STUDENT_ID,
    CONF_STUDENT_NAME,
    DEFAULT_CALENDAR_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import ClassevivaCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.CALENDAR]

SERVICE_REFRESH_DATA = "refresh_data"

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate config entry from older version."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new_data = {**config_entry.data}
        new_data.setdefault(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        new_data.setdefault(CONF_CALENDAR_NAME, DEFAULT_CALENDAR_NAME)
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2
        )

    _LOGGER.debug("Migration to version %s successful", config_entry.version)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Classeviva from a config entry."""
    student_id = entry.data[CONF_STUDENT_ID]
    password = entry.data[CONF_PASSWORD]
    student_name = entry.data.get(CONF_STUDENT_NAME, student_id)
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    api = ClassevivaAPI(hass, student_id, password)

    try:
        await api.authenticate()
    except ConfigEntryAuthFailed:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "reauth", "entry_id": entry.entry_id},
                data=entry.data,
            )
        )
        return False

    coordinator = ClassevivaCoordinator(
        hass, api, entry.entry_id, student_id, student_name,
        scan_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH_DATA):

        async def handle_refresh(call: ServiceCall) -> None:
            ent_reg = er.async_get(hass)
            coordinators: set[ClassevivaCoordinator] = set()

            if entity_ids := call.data.get("entity_id"):
                if isinstance(entity_ids, str):
                    entity_ids = [entity_ids]
                for entity_id in entity_ids:
                    ent_entry = ent_reg.async_get(entity_id)
                    if ent_entry and ent_entry.config_entry_id:
                        coord = hass.data[DOMAIN].get(ent_entry.config_entry_id)
                        if coord:
                            coordinators.add(coord)
            else:
                coordinators.update(hass.data[DOMAIN].values())

            for coord in coordinators:
                await coord.async_request_refresh()

        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH_DATA,
            handle_refresh,
            schema=vol.Schema(
                {vol.Optional("entity_id"): vol.Any(str, [str])}
            ),
        )

    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH_DATA)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
