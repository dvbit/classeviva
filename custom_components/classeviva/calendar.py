"""Calendar platform for Classeviva integration."""
from __future__ import annotations

from datetime import datetime, date, timedelta
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CALENDAR_NAME, DEFAULT_CALENDAR_NAME, DOMAIN
from .coordinator import ClassevivaCoordinator

_LOGGER = logging.getLogger(__name__)

ABSENCE_LABELS = {"ABA0": "Assenza", "ABR0": "Ritardo", "ABU0": "Uscita anticipata"}


def _to_date(val: Any) -> date | None:
    """Parse a date string into a date object."""
    if not val:
        return None
    if not isinstance(val, str):
        return None
    # Strip to first 10 chars for YYYY-MM-DD
    raw = val[:10]
    try:
        return date.fromisoformat(raw)
    except (ValueError, TypeError):
        pass
    # Try full ISO datetime
    try:
        return datetime.fromisoformat(val).date()
    except (ValueError, TypeError):
        _LOGGER.warning("Cannot parse date: %r", val)
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ClassevivaCoordinator = hass.data[DOMAIN][entry.entry_id]
    prefix = entry.data.get(CONF_CALENDAR_NAME, DEFAULT_CALENDAR_NAME)

    entities = [
        ClassevivaCalendarVoti(coordinator, prefix),
        ClassevivaCalendarAssenze(coordinator, prefix),
        ClassevivaCalendarCompiti(coordinator, prefix),
        ClassevivaCalendarNote(coordinator, prefix),
    ]

    _LOGGER.info("Setting up %d Classeviva calendar entities", len(entities))
    async_add_entities(entities, True)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class ClassevivaCalendarBase(CoordinatorEntity[ClassevivaCoordinator], CalendarEntity):
    """Base calendar entity. Does NOT use has_entity_name so the name is set directly."""

    def __init__(self, coordinator: ClassevivaCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.student_id}_cal_{key}"
        self._attr_name = name
        self._attr_has_entity_name = False
        self._events: list[CalendarEvent] = []

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next or most recent event."""
        if not self._events:
            return None
        today = date.today()
        # Find the first event ending after today
        for e in self._events:
            if e.end > today:
                return e
        # If no future events, return the most recent
        return self._events[-1]

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return events in the given date range."""
        sd = start_date.date() if isinstance(start_date, datetime) else start_date
        ed = end_date.date() if isinstance(end_date, datetime) else end_date
        result = [e for e in self._events if e.start >= sd and e.start < ed]
        _LOGGER.debug(
            "async_get_events %s: range %s to %s, returning %d of %d total",
            self._attr_name, sd, ed, len(result), len(self._events),
        )
        return result


# ---------------------------------------------------------------------------
# Voti calendar — every grade as an all-day event
# ---------------------------------------------------------------------------

class ClassevivaCalendarVoti(ClassevivaCalendarBase):
    def __init__(self, coordinator: ClassevivaCoordinator, prefix: str) -> None:
        super().__init__(coordinator, "voti", f"{prefix} Voti")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            _LOGGER.debug("Cal Voti: no data")
            return
        events: list[CalendarEvent] = []
        voti = data.get("voti", [])
        for voto in voti:
            dt = _to_date(voto.get("evtDate"))
            if not dt:
                continue
            materia = voto.get("subjectDesc", "")
            display = voto.get("displayValue", "")
            comp = voto.get("componentDesc", "")
            comment = voto.get("notesForFamily", "")

            summary = f"{display} - {materia}"
            if comp:
                summary += f" ({comp})"

            events.append(CalendarEvent(
                start=dt,
                end=dt + timedelta(days=1),
                summary=summary,
                description=comment if comment else None,
            ))
        events.sort(key=lambda e: e.start)
        self._events = events
        _LOGGER.info("Cal Voti: %d events from %d grades", len(events), len(voti))
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# Assenze calendar
# ---------------------------------------------------------------------------

class ClassevivaCalendarAssenze(ClassevivaCalendarBase):
    def __init__(self, coordinator: ClassevivaCoordinator, prefix: str) -> None:
        super().__init__(coordinator, "assenze", f"{prefix} Assenze")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        events: list[CalendarEvent] = []
        assenze = data.get("assenze", [])
        for a in assenze:
            dt = _to_date(a.get("evtDate"))
            if not dt:
                continue
            code = a.get("evtCode", "")
            label = ABSENCE_LABELS.get(code, code)
            justified = a.get("isJustified", False)
            reason = a.get("justifReasonDesc", "")

            summary = label
            if justified:
                summary += " (giustificata)"

            events.append(CalendarEvent(
                start=dt,
                end=dt + timedelta(days=1),
                summary=summary,
                description=reason if reason else None,
            ))
        events.sort(key=lambda e: e.start)
        self._events = events
        _LOGGER.info("Cal Assenze: %d events from %d absences", len(events), len(assenze))
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# Compiti calendar
# ---------------------------------------------------------------------------

class ClassevivaCalendarCompiti(ClassevivaCalendarBase):
    def __init__(self, coordinator: ClassevivaCoordinator, prefix: str) -> None:
        super().__init__(coordinator, "compiti", f"{prefix} Compiti")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        events: list[CalendarEvent] = []
        agenda = data.get("agenda", [])
        for c in agenda:
            raw_date = c.get("evtDatetimeBegin") or c.get("evtDate")
            dt = _to_date(raw_date)
            if not dt:
                _LOGGER.debug("Cal Compiti: skip, bad date: %r", raw_date)
                continue
            materia = c.get("subjectDesc", "")
            notes = c.get("notes", "")
            autore = c.get("authorName", "")

            summary = f"Compito: {materia}" if materia else "Compito"
            desc_parts = []
            if notes:
                desc_parts.append(notes)
            if autore:
                desc_parts.append(f"Prof. {autore}")
            desc = "\n".join(desc_parts) if desc_parts else None

            events.append(CalendarEvent(
                start=dt,
                end=dt + timedelta(days=1),
                summary=summary,
                description=desc,
            ))
        events.sort(key=lambda e: e.start)
        self._events = events
        _LOGGER.info("Cal Compiti: %d events from %d agenda items", len(events), len(agenda))
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# Note calendar
# ---------------------------------------------------------------------------

class ClassevivaCalendarNote(ClassevivaCalendarBase):
    def __init__(self, coordinator: ClassevivaCoordinator, prefix: str) -> None:
        super().__init__(coordinator, "note", f"{prefix} Note")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        events: list[CalendarEvent] = []
        note = data.get("note", [])
        for n in note:
            dt = _to_date(n.get("evtDate"))
            if not dt:
                continue
            autore = n.get("authorName", "")
            testo = n.get("evtText", "")

            summary = f"Nota: {autore}" if autore else "Nota disciplinare"

            events.append(CalendarEvent(
                start=dt,
                end=dt + timedelta(days=1),
                summary=summary,
                description=testo if testo else None,
            ))
        events.sort(key=lambda e: e.start)
        self._events = events
        _LOGGER.info("Cal Note: %d events from %d notes", len(events), len(note))
        self.async_write_ha_state()
