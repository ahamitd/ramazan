"""Data update coordinator for Ramazan integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DiyanetApiClient, DiyanetApiError
from .const import CONF_CITY_ID, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class RamazanDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Ramazan prayer time data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.city_id = entry.data[CONF_CITY_ID]
        self.city_name = entry.data.get("city", "")
        self.state_name = entry.data.get("state", "")

        session = async_get_clientsession(hass)
        self.api = DiyanetApiClient(session)

        self._monthly_data: list[dict[str, Any]] = []
        # Cached data for fallback when API is unreachable
        self._cached_data: dict[str, Any] | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Diyanet API."""
        _LOGGER.debug(
            "Fetching Diyanet prayer times for %s (city_id: %s)",
            self.location_name,
            self.city_id,
        )
        try:
            # Fetch monthly data
            self._monthly_data = await self.api.get_monthly_prayer_times(self.city_id)

            if not self._monthly_data:
                raise UpdateFailed("No prayer time data received")

            # Find today's data
            today = datetime.now()
            today_str = today.strftime("%d.%m.%Y")

            today_data = None
            tomorrow_data = None
            tomorrow_str = (today + timedelta(days=1)).strftime("%d.%m.%Y")

            for day_data in self._monthly_data:
                greg_date = day_data.get("gregorianDateShort", "")
                if greg_date == today_str:
                    today_data = day_data
                elif greg_date == tomorrow_str:
                    tomorrow_data = day_data

            if today_data is None:
                # If today's data not found (month boundary), use first available
                _LOGGER.warning(
                    "Today's data (%s) not found in monthly data, using first entry",
                    today_str,
                )
                today_data = self._monthly_data[0] if self._monthly_data else {}

            # Build result and cache it for future fallback
            result = {
                "today": today_data,
                "tomorrow": tomorrow_data,
                "monthly": self._monthly_data,
            }
            self._cached_data = result

            return result

        except DiyanetApiError as err:
            if self._cached_data is not None:
                _LOGGER.warning(
                    "Error fetching Diyanet data (%s). Using cached data from last successful fetch.",
                    err,
                )
                return self._cached_data
            raise UpdateFailed(f"Error fetching Diyanet data: {err}") from err

        except Exception as err:
            if self._cached_data is not None:
                _LOGGER.warning(
                    "Unexpected error fetching prayer time data (%s). Using cached data.",
                    err,
                )
                return self._cached_data
            _LOGGER.exception("Unexpected error fetching prayer time data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

    @property
    def location_name(self) -> str:
        """Return the location name."""
        if self.city_name:
            return f"{self.city_name}, {self.state_name}"
        return self.state_name
