"""API wrapper for Classeviva REST API."""
from __future__ import annotations

from datetime import datetime
import json
import logging
import re
from typing import Any

import requests
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://web.spaggiari.eu/rest/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
HEADERS = {
    "content-type": "application/json",
    "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
    "User-Agent": "CVVS/std/4.2.3 Android/12",
}


class ClassevivaAPI:
    """Direct REST API wrapper for Classeviva."""

    def __init__(self, hass: HomeAssistant, student_id: str, password: str) -> None:
        self.hass = hass
        self.student_id = student_id
        self.password = password
        self._session: requests.Session | None = None
        self._user_id: str | None = None
        self._user_type: str | None = None  # "students" or "parents"

    def _do_login(self) -> None:
        """Perform login and determine user type and ID."""
        session = requests.Session()
        payload = json.dumps({
            "ident": None,
            "pass": self.password,
            "uid": self.student_id,
        })
        resp = session.post(LOGIN_URL, headers=HEADERS, data=payload)

        if resp.status_code == 422:
            raise ConfigEntryAuthFailed("Credenziali non valide")
        if resp.status_code != 200:
            raise Exception(
                f"Errore login HTTP {resp.status_code}: {resp.text}"
            )

        data = resp.json()
        token = data.get("token", "")
        ident = data.get("ident", "")

        _LOGGER.debug("Login OK, ident=%s, keys=%s", ident, list(data.keys()))

        # Add auth token to session
        session.headers.update({
            **HEADERS,
            "Z-Auth-Token": token,
        })

        # Extract numeric user ID (strip all letters)
        numeric_id = re.sub(r"\D", "", ident)

        if ident.startswith("S"):
            self._user_type = "students"
            self._user_id = numeric_id
        elif ident.startswith("G"):
            self._user_type = "parents"
            self._user_id = numeric_id
        else:
            # Fallback: try as student
            self._user_type = "students"
            self._user_id = numeric_id

        _LOGGER.debug(
            "User type=%s, user_id=%s", self._user_type, self._user_id
        )
        self._session = session

    async def authenticate(self) -> None:
        """Authenticate with Classeviva."""
        try:
            await self.hass.async_add_executor_job(self._do_login)
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.exception("Errore comunicazione con Classeviva")
            raise Exception(
                f"Errore comunicazione con Classeviva: {err}"
            ) from err

    def _ensure_session(self) -> requests.Session:
        if self._session is None:
            self._do_login()
        return self._session

    def _api_get(self, path: str) -> Any:
        """Make an authenticated GET request."""
        session = self._ensure_session()
        url = f"{BASE_URL}/{self._user_type}/{self._user_id}/{path}"
        _LOGGER.debug("GET %s", url)
        resp = session.get(url)
        if resp.status_code == 200:
            return resp.json()
        # If we get 404 with "invalid student-id" and we're using parents,
        # try with students endpoint
        if resp.status_code == 404 and self._user_type == "parents":
            url_student = f"{BASE_URL}/students/{self._user_id}/{path}"
            _LOGGER.debug("Retry as student: GET %s", url_student)
            resp2 = session.get(url_student)
            if resp2.status_code == 200:
                # Switch to students for future calls
                self._user_type = "students"
                return resp2.json()
        _LOGGER.error("API error %s for %s: %s", resp.status_code, path, resp.text)
        raise Exception(f"Errore API {resp.status_code}: {resp.text}")

    async def _async_api_get(self, path: str) -> Any:
        await self._async_ensure_connected()
        return await self.hass.async_add_executor_job(self._api_get, path)

    async def _async_ensure_connected(self) -> None:
        if self._session is None:
            await self.authenticate()

    async def fetch_voti(self) -> list[dict[str, Any]]:
        """Grades - no date filtering available."""
        data = await self._async_api_get("grades")
        result = data.get("grades", [])
        _LOGGER.debug("fetch_voti: %d grades returned", len(result))
        return result

    async def fetch_assenze(self) -> list[dict[str, Any]]:
        """Absences - always fetch all."""
        data = await self._async_api_get("absences/details")
        result = data.get("events", [])
        _LOGGER.debug("fetch_assenze: %d events returned", len(result))
        return result

    async def fetch_agenda(self) -> list[dict[str, Any]]:
        """Agenda - full school year."""
        today = datetime.now()
        if today.month >= 9:
            year_start = f"{today.year}0901"
            year_end = f"{today.year + 1}0630"
        else:
            year_start = f"{today.year - 1}0901"
            year_end = f"{today.year}0630"
        data = await self._async_api_get(f"agenda/all/{year_start}/{year_end}")
        result = data.get("agenda", [])
        _LOGGER.debug("fetch_agenda: %d items returned", len(result))
        return result

    async def fetch_note(self) -> dict[str, Any]:
        """Notes - no date filtering available."""
        data = await self._async_api_get("notes/all")
        _LOGGER.debug("fetch_note: keys=%s", list(data.keys()) if isinstance(data, dict) else type(data).__name__)
        return data

    async def fetch_materie(self) -> list[dict[str, Any]]:
        """Subjects."""
        data = await self._async_api_get("subjects")
        result = data.get("subjects", [])
        _LOGGER.debug("fetch_materie: %d subjects returned", len(result))
        return result
