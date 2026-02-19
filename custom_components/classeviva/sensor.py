"""Sensor platform for Classeviva integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_IMPORT_HISTORY, DOMAIN
from .coordinator import ClassevivaCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_date(val: Any) -> datetime | None:
    if not val or not isinstance(val, str):
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _safe_attr_key(name: str) -> str:
    """Convert a subject name to a safe attribute key."""
    key = name.lower().replace(" ", "_").replace("'", "").replace("à", "a").replace("è", "e").replace("é", "e").replace("ì", "i").replace("ò", "o").replace("ù", "u")
    return "".join(c for c in key if c.isalnum() or c == "_")


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ClassevivaCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors: list[SensorEntity] = [
        ClassevivaMediaGenerale(coordinator),
        ClassevivaUltimoVoto(coordinator),
        ClassevivaAssenze(coordinator),
        ClassevivaRitardi(coordinator),
        ClassevivaUscite(coordinator),
        ClassevivaCompiti(coordinator),
        ClassevivaNote(coordinator),
        ClassevivaLastUpdate(coordinator),
    ]

    if coordinator.data:
        sensors.extend(_create_subject_sensors(coordinator))

    async_add_entities(sensors, True)


def _create_subject_sensors(coordinator: ClassevivaCoordinator) -> list[SensorEntity]:
    voti = coordinator.data.get("voti", [])
    seen: set[str] = set()
    sensors: list[SensorEntity] = []
    for voto in voti:
        materia = voto.get("subjectDesc", "")
        if materia and materia not in seen:
            seen.add(materia)
            sensors.append(ClassevivaMediaMateria(coordinator, materia))
    return sensors


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class ClassevivaBaseSensor(CoordinatorEntity[ClassevivaCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ClassevivaCoordinator, key: str, name: str, icon: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.student_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon


# ---------------------------------------------------------------------------
# VOTI — Media Generale
# Stato: media numerica. Attributi: un attributo per materia (media_MATERIA).
# ---------------------------------------------------------------------------

class ClassevivaMediaGenerale(ClassevivaBaseSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ClassevivaCoordinator) -> None:
        super().__init__(coordinator, "media_generale", "Media Generale", "mdi:school")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        voti = data.get("voti", [])
        valori = []
        for v in voti:
            val = v.get("decimalValue")
            if val is not None:
                try:
                    valori.append(float(val))
                except (ValueError, TypeError):
                    continue
        self._attr_native_value = round(sum(valori) / len(valori), 2) if valori else None

        # Flatten medie_materie into individual attributes: media_matematica, media_italiano, ...
        medie = data.get("medie_materie", {})
        attrs: dict[str, Any] = {"voti_totali": len(voti)}
        for materia, media in medie.items():
            attrs[f"media_{_safe_attr_key(materia)}"] = media
        self._attr_extra_state_attributes = attrs
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# VOTI — Ultimo Voto
# Stato: valore numerico del voto (decimalValue) → grafico in history.
# Attributi: materia, data, voto (display), tipo, commento.
# ---------------------------------------------------------------------------

class ClassevivaUltimoVoto(ClassevivaBaseSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ClassevivaCoordinator) -> None:
        super().__init__(coordinator, "ultimo_voto", "Ultimo Voto", "mdi:star")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        voti = data.get("voti", [])
        if not voti:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            self.async_write_ha_state()
            return
        ultimo = sorted(voti, key=lambda v: v.get("evtDate", ""), reverse=True)[0]
        try:
            self._attr_native_value = float(ultimo.get("decimalValue", 0) or 0)
        except (ValueError, TypeError):
            self._attr_native_value = None
        self._attr_extra_state_attributes = {
            "materia": ultimo.get("subjectDesc", ""),
            "data": ultimo.get("evtDate", ""),
            "voto": ultimo.get("displayValue", ""),
            "tipo": ultimo.get("componentDesc", ""),
            "commento": ultimo.get("notesForFamily", ""),
        }
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# VOTI — Media per Materia
# Stato: media numerica. Attributi: ultimo voto della materia.
# ---------------------------------------------------------------------------

class ClassevivaMediaMateria(ClassevivaBaseSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ClassevivaCoordinator, materia: str) -> None:
        safe_key = _safe_attr_key(materia)
        super().__init__(coordinator, f"media_{safe_key}", f"Media {materia}", "mdi:book-open-variant")
        self._materia = materia

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener, then backfill historical grades if requested."""
        await super().async_added_to_hass()
        if self.coordinator.config_entry.data.get(CONF_IMPORT_HISTORY):
            await self._maybe_inject_history()

    async def _maybe_inject_history(self) -> None:
        """Inject historical grade states only once per entity (persisted across restarts)."""
        store = Store(
            self.hass, 1,
            f"{DOMAIN}_histimport_{self.coordinator.entry_id}_{_safe_attr_key(self._materia)}",
        )
        if await store.async_load():
            return  # Already imported in a previous session
        await self._inject_historical_states()
        await store.async_save({"done": True})

    async def _inject_historical_states(self) -> None:
        """Write each past grade as a distinct state change with its actual date."""
        data = self.coordinator.data
        if not data:
            return
        voti = sorted(
            [v for v in data.get("voti", []) if v.get("subjectDesc") == self._materia],
            key=lambda x: x.get("evtDate", ""),
        )
        if not voti:
            return

        day_counts: dict[str, int] = {}
        written = 0
        for voto in voti:
            date_str = voto.get("evtDate", "")
            if not date_str:
                continue
            try:
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            try:
                val = round(float(voto.get("decimalValue", 0) or 0), 2)
            except (ValueError, TypeError):
                continue

            # Grades on the same day get +1s offsets so the recorder sees distinct events
            day_key = date_str[:10]
            sec_offset = day_counts.get(day_key, 0)
            day_counts[day_key] = sec_offset + 1
            ts = dt.timestamp() + sec_offset

            self.hass.states.async_set(
                self.entity_id,
                str(val),
                {
                    "data": date_str,
                    "voto": voto.get("displayValue", ""),
                    "tipo": voto.get("componentDesc", ""),
                    "commento": voto.get("notesForFamily", ""),
                },
                force_update=True,
                timestamp=ts,
            )
            written += 1
            await asyncio.sleep(0)  # yield to event loop between writes

        # Restore current state (latest grade at now) after injection
        self._handle_coordinator_update()
        _LOGGER.info(
            "Classeviva: injected %d historical grades for %s", written, self._materia
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        voti = sorted(
            [v for v in data.get("voti", []) if v.get("subjectDesc") == self._materia],
            key=lambda x: x.get("evtDate", ""),
        )
        valori = []
        for v in voti:
            val = v.get("decimalValue")
            if val is not None:
                try:
                    valori.append(float(val))
                except (ValueError, TypeError):
                    continue

        if voti:
            ultimo = voti[-1]  # most recent (sorted ascending by date)
            try:
                self._attr_native_value = float(ultimo.get("decimalValue", 0) or 0)
            except (ValueError, TypeError):
                self._attr_native_value = None
            self._attr_extra_state_attributes = {
                "media": round(sum(valori) / len(valori), 2) if valori else None,
                "min_voto": round(min(valori), 2) if valori else None,
                "max_voto": round(max(valori), 2) if valori else None,
                "num_voti": len(voti),
                "data": ultimo.get("evtDate", ""),
                "voto": ultimo.get("displayValue", ""),
                "tipo": ultimo.get("componentDesc", ""),
                "commento": ultimo.get("notesForFamily", ""),
            }
        else:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {
                "media": None, "min_voto": None, "max_voto": None, "num_voti": 0,
            }
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# ASSENZE / RITARDI / USCITE
# Stato: conteggio numerico (intero). Attributi: ultimo evento.
# ---------------------------------------------------------------------------

class ClassevivaAssenze(ClassevivaBaseSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "assenze"

    def __init__(self, coordinator: ClassevivaCoordinator) -> None:
        super().__init__(coordinator, "assenze", "Assenze", "mdi:calendar-remove")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        filtrate = sorted(
            [a for a in data.get("assenze", []) if a.get("evtCode") == "ABA0"],
            key=lambda x: x.get("evtDate", ""), reverse=True,
        )
        self._attr_native_value = len(filtrate)
        self._attr_extra_state_attributes = {
            "data": filtrate[0].get("evtDate", "") if filtrate else "",
            "giustificata": filtrate[0].get("isJustified", False) if filtrate else False,
            "motivo": filtrate[0].get("justifReasonDesc", "") if filtrate else "",
        }
        self.async_write_ha_state()


class ClassevivaRitardi(ClassevivaBaseSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "ritardi"

    def __init__(self, coordinator: ClassevivaCoordinator) -> None:
        super().__init__(coordinator, "ritardi", "Ritardi", "mdi:clock-alert")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        filtrate = sorted(
            [a for a in data.get("assenze", []) if a.get("evtCode") == "ABR0"],
            key=lambda x: x.get("evtDate", ""), reverse=True,
        )
        self._attr_native_value = len(filtrate)
        self._attr_extra_state_attributes = {
            "data": filtrate[0].get("evtDate", "") if filtrate else "",
            "giustificata": filtrate[0].get("isJustified", False) if filtrate else False,
        }
        self.async_write_ha_state()


class ClassevivaUscite(ClassevivaBaseSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "uscite"

    def __init__(self, coordinator: ClassevivaCoordinator) -> None:
        super().__init__(coordinator, "uscite_anticipate", "Uscite Anticipate", "mdi:door-open")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        filtrate = sorted(
            [a for a in data.get("assenze", []) if a.get("evtCode") == "ABU0"],
            key=lambda x: x.get("evtDate", ""), reverse=True,
        )
        self._attr_native_value = len(filtrate)
        self._attr_extra_state_attributes = {
            "data": filtrate[0].get("evtDate", "") if filtrate else "",
            "giustificata": filtrate[0].get("isJustified", False) if filtrate else False,
        }
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# AGENDA — Compiti
# Stato: numero compiti futuri. Attributi: prossimo compito.
# ---------------------------------------------------------------------------

class ClassevivaCompiti(ClassevivaBaseSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "compiti"

    def __init__(self, coordinator: ClassevivaCoordinator) -> None:
        super().__init__(coordinator, "compiti", "Compiti da Fare", "mdi:notebook")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        agenda = data.get("agenda", [])
        oggi = datetime.now().date()
        futuri = []
        for c in agenda:
            dt = _parse_date(c.get("evtDatetimeBegin") or c.get("evtDate"))
            if dt and dt.date() >= oggi:
                futuri.append(c)
        futuri.sort(key=lambda x: x.get("evtDatetimeBegin") or x.get("evtDate", ""))

        self._attr_native_value = len(futuri)
        if futuri:
            prossimo = futuri[0]
            dt = _parse_date(prossimo.get("evtDatetimeBegin") or prossimo.get("evtDate"))
            self._attr_extra_state_attributes = {
                "data": str(dt.date()) if dt else "",
                "materia": prossimo.get("subjectDesc", ""),
                "descrizione": prossimo.get("notes", ""),
                "autore": prossimo.get("authorName", ""),
            }
        else:
            self._attr_extra_state_attributes = {}
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# NOTE
# Stato: numero note. Attributi: ultima nota.
# ---------------------------------------------------------------------------

class ClassevivaNote(ClassevivaBaseSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "note"

    def __init__(self, coordinator: ClassevivaCoordinator) -> None:
        super().__init__(coordinator, "note", "Note Disciplinari", "mdi:alert")

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        ordinate = sorted(
            data.get("note", []),
            key=lambda x: x.get("evtDate", ""), reverse=True,
        )
        self._attr_native_value = len(ordinate)
        self._attr_extra_state_attributes = {
            "data": ordinate[0].get("evtDate", "") if ordinate else "",
            "testo": ordinate[0].get("evtText", "") if ordinate else "",
            "autore": ordinate[0].get("authorName", "") if ordinate else "",
            "letta": ordinate[0].get("readStatus", False) if ordinate else False,
        }
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# LAST UPDATE
# ---------------------------------------------------------------------------

class ClassevivaLastUpdate(ClassevivaBaseSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: ClassevivaCoordinator) -> None:
        super().__init__(coordinator, "ultimo_aggiornamento", "Ultimo Aggiornamento", "mdi:clock-check")

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.coordinator.last_successful_update
        self.async_write_ha_state()
