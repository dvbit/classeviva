"""DataUpdateCoordinator for Classeviva integration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ClassevivaAPI
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

NOTE_CATEGORIES = ("NTTE", "NTCL", "NTWN", "NTST")


class ClassevivaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for managing Classeviva data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ClassevivaAPI,
        entry_id: str,
        student_id: str,
        student_name: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        self.api = api
        self.entry_id = entry_id
        self.student_id = student_id
        self.student_name = student_name
        self.last_successful_update: datetime | None = None

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, student_id)},
            name=f"Classeviva - {student_name}",
            manufacturer="Spaggiari",
            model="Registro Elettronico",
            sw_version="2.0",
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{student_id}",
            update_interval=timedelta(minutes=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            await self.api.authenticate()

            voti = await self.api.fetch_voti()
            assenze = await self.api.fetch_assenze()
            agenda = await self.api.fetch_agenda()
            note_raw = await self.api.fetch_note()

            _LOGGER.info(
                "Classeviva fetch: voti=%d, assenze=%d, agenda=%d",
                len(voti) if isinstance(voti, list) else 0,
                len(assenze) if isinstance(assenze, list) else 0,
                len(agenda) if isinstance(agenda, list) else 0,
            )

            # Parse notes from categorized dict
            note_list: list[dict[str, Any]] = []
            if isinstance(note_raw, dict):
                for cat in NOTE_CATEGORIES:
                    items = note_raw.get(cat, [])
                    if isinstance(items, list):
                        note_list.extend(items)
                _LOGGER.debug("Notes: %d total from categories %s",
                              len(note_list), list(note_raw.keys()))
            else:
                _LOGGER.warning("Notes response is not a dict: %s", type(note_raw).__name__)

            medie_materie = self._calcola_medie(voti)

            result: dict[str, Any] = {
                "voti": voti if isinstance(voti, list) else [],
                "assenze": assenze if isinstance(assenze, list) else [],
                "agenda": agenda if isinstance(agenda, list) else [],
                "note": note_list,
                "medie_materie": medie_materie,
            }

            self.last_successful_update = datetime.now(timezone.utc)

            return result

        except ConfigEntryAuthFailed:
            _LOGGER.error("Autenticazione fallita, trigger reauth")
            raise
        except Exception as err:
            _LOGGER.exception("Errore update dati: %s", err)
            raise UpdateFailed(f"Errore comunicazione con Classeviva: {err}") from err

    @staticmethod
    def _calcola_medie(voti: list[dict[str, Any]]) -> dict[str, float]:
        if not voti:
            return {}
        per_materia: dict[str, list[float]] = {}
        for voto in voti:
            materia = voto.get("subjectDesc", "")
            valore = voto.get("decimalValue")
            if materia and valore is not None:
                try:
                    per_materia.setdefault(materia, []).append(float(valore))
                except (ValueError, TypeError):
                    continue
        return {
            m: round(sum(v) / len(v), 2)
            for m, v in per_materia.items() if v
        }
