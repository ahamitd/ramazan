"""Diyanet API client for Ramazan integration."""
from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from .const import (
    API_AUTH_ENDPOINT,
    API_BASE_URL,
    API_CITIES_ENDPOINT,
    API_CLIENT_ID,
    API_CLIENT_SECRET,
    API_COUNTRIES_ENDPOINT,
    API_PASSWORD,
    API_PRAYER_TIMES_ENDPOINT,
    API_STATES_ENDPOINT,
    API_USERNAME,
)

_LOGGER = logging.getLogger(__name__)


class DiyanetApiError(Exception):
    """Exception for Diyanet API errors."""


class DiyanetApiClient:
    """Client for Diyanet AwqatSalah API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._session = session
        self._token: str | None = None
        self._token_expires_at: float = 0

    async def _ensure_token(self) -> None:
        """Ensure we have a valid JWT token, refresh if expired."""
        if self._token and time.time() < self._token_expires_at:
            return

        try:
            data = {
                "client_id": API_CLIENT_ID,
                "client_secret": API_CLIENT_SECRET,
                "grant_type": "password",
                "username": API_USERNAME,
                "password": API_PASSWORD,
            }

            async with self._session.post(
                f"{API_BASE_URL}{API_AUTH_ENDPOINT}",
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "dib_super_app/40 CFNetwork/3860.300.31 Darwin/25.2.0",
                },
            ) as resp:
                if resp.status != 200:
                    raise DiyanetApiError(
                        f"Auth failed with status {resp.status}"
                    )
                result = await resp.json()
                self._token = result.get("access_token")
                # Token expires in ~10 minutes, refresh 1 minute early
                expires_in_ms = result.get("expires_in", 600000)
                self._token_expires_at = time.time() + (expires_in_ms / 1000) - 60

                _LOGGER.debug("Got new Diyanet API token, expires in %s ms", expires_in_ms)

        except aiohttp.ClientError as err:
            raise DiyanetApiError(f"Connection error during auth: {err}") from err

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth token."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "tr-TR,tr;q=0.9",
            "X-Source-Page": "mihrapp-superapp",
            "User-Agent": "dib_super_app/40 CFNetwork/3860.300.31 Darwin/25.2.0",
        }

    async def _request(self, endpoint: str) -> Any:
        """Make an authenticated API request."""
        await self._ensure_token()

        url = f"{API_BASE_URL}{endpoint}"
        _LOGGER.debug("Requesting: %s", url)

        try:
            async with self._session.get(
                url,
                headers=self._get_headers(),
            ) as resp:
                if resp.status != 200:
                    raise DiyanetApiError(
                        f"API request failed: {resp.status} for {endpoint}"
                    )
                result = await resp.json()

                if isinstance(result, dict):
                    if not result.get("success", True):
                        raise DiyanetApiError(
                            f"API error: {result.get('message', 'Unknown error')}"
                        )
                    return result.get("data", result)

                return result

        except aiohttp.ClientError as err:
            raise DiyanetApiError(f"Connection error: {err}") from err

    async def get_countries(self) -> list[dict[str, Any]]:
        """Get list of countries."""
        return await self._request(API_COUNTRIES_ENDPOINT)

    async def get_states(self, country_id: int) -> list[dict[str, Any]]:
        """Get list of states/provinces for a country."""
        return await self._request(f"{API_STATES_ENDPOINT}/{country_id}")

    async def get_cities(self, state_id: int) -> list[dict[str, Any]]:
        """Get list of cities for a state."""
        return await self._request(f"{API_CITIES_ENDPOINT}/{state_id}")

    async def get_monthly_prayer_times(self, city_id: int) -> list[dict[str, Any]]:
        """Get monthly prayer times for a city."""
        return await self._request(f"{API_PRAYER_TIMES_ENDPOINT}/{city_id}")

    async def validate_city(self, city_id: int) -> bool:
        """Validate that a city_id returns valid prayer time data."""
        try:
            data = await self.get_monthly_prayer_times(city_id)
            return isinstance(data, list) and len(data) > 0
        except DiyanetApiError:
            return False
