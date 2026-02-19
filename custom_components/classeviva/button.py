"""Button platform for Classeviva integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ClassevivaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Classeviva buttons from config entry."""
    coordinator: ClassevivaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ClassevivaRefreshButton(coordinator)])


class ClassevivaRefreshButton(ButtonEntity):
    """Button to trigger a manual data refresh."""

    _attr_has_entity_name = True
    _attr_name = "Aggiorna Dati"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: ClassevivaCoordinator) -> None:
        """Initialize button."""
        self._coordinator = coordinator
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.student_id}_refresh"

    async def async_press(self) -> None:
        """Handle button press."""
        await self._coordinator.async_request_refresh()
