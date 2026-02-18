"""Config flow for Ramazan integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DiyanetApiClient, DiyanetApiError
from .const import (
    CONF_CITY,
    CONF_CITY_ID,
    CONF_COUNTRY,
    CONF_COUNTRY_ID,
    CONF_STATE,
    CONF_STATE_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class RamazanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ramazan."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._countries: list[dict[str, Any]] = []
        self._states: list[dict[str, Any]] = []
        self._cities: list[dict[str, Any]] = []
        self._selected_country: str | None = None
        self._selected_country_id: int | None = None
        self._selected_state: str | None = None
        self._selected_state_id: int | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - country selection."""
        errors: dict[str, str] = {}

        if not self._countries:
            try:
                session = async_get_clientsession(self.hass)
                client = DiyanetApiClient(session)
                self._countries = await client.get_countries()
            except DiyanetApiError:
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({}),
                    errors=errors,
                )

        if user_input is not None:
            country_name = user_input[CONF_COUNTRY]

            # Find country ID
            for country in self._countries:
                name = country.get("name") or country.get("countryName") or ""
                if name == country_name:
                    self._selected_country = country_name
                    self._selected_country_id = country.get("id") or country.get("countryId")
                    break

            if self._selected_country_id:
                try:
                    session = async_get_clientsession(self.hass)
                    client = DiyanetApiClient(session)
                    self._states = await client.get_states(self._selected_country_id)
                except DiyanetApiError:
                    errors["base"] = "cannot_connect"
                    return self._show_country_form(errors)

                return await self.async_step_state()

            errors["base"] = "invalid_country"

        return self._show_country_form(errors)

    def _show_country_form(self, errors: dict[str, str]) -> FlowResult:
        """Show the country selection form."""
        country_names = sorted([
            c.get("name") or c.get("countryName") or ""
            for c in self._countries
        ])
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COUNTRY): vol.In(country_names),
                }
            ),
            errors=errors,
        )

    async def async_step_state(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the second step - state/province selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            state_name = user_input[CONF_STATE]

            # Find state ID
            for state in self._states:
                name = state.get("name") or state.get("stateName") or ""
                if name == state_name:
                    self._selected_state = state_name
                    self._selected_state_id = state.get("id") or state.get("stateId")
                    break

            if self._selected_state_id:
                try:
                    session = async_get_clientsession(self.hass)
                    client = DiyanetApiClient(session)
                    self._cities = await client.get_cities(self._selected_state_id)
                except DiyanetApiError:
                    errors["base"] = "cannot_connect"
                    return self._show_state_form(errors)

                return await self.async_step_city()

            errors["base"] = "invalid_state"

        return self._show_state_form(errors)

    def _show_state_form(self, errors: dict[str, str]) -> FlowResult:
        """Show the state selection form."""
        state_names = sorted([
            s.get("name") or s.get("stateName") or ""
            for s in self._states
        ])
        return self.async_show_form(
            step_id="state",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATE): vol.In(state_names),
                }
            ),
            errors=errors,
            description_placeholders={"country": self._selected_country},
        )

    async def async_step_city(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the third step - city selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            city_name = user_input[CONF_CITY]

            # Find city ID
            selected_city = None
            for city in self._cities:
                name = city.get("name") or city.get("cityName") or ""
                if name == city_name:
                    selected_city = city
                    break

            if selected_city:
                city_id = selected_city.get("id") or selected_city.get("cityId")

                if city_id:
                    # Check for existing entry with same city_id
                    await self.async_set_unique_id(f"ramazan_{city_id}")
                    self._abort_if_unique_id_configured()

                    try:
                        session = async_get_clientsession(self.hass)
                        client = DiyanetApiClient(session)
                        valid = await client.validate_city(city_id)
                        if not valid:
                            errors["base"] = "cannot_connect"
                        else:
                            return self.async_create_entry(
                                title=f"{city_name}, {self._selected_state}",
                                data={
                                    CONF_COUNTRY: self._selected_country,
                                    CONF_COUNTRY_ID: self._selected_country_id,
                                    CONF_STATE: self._selected_state,
                                    CONF_STATE_ID: self._selected_state_id,
                                    CONF_CITY: city_name,
                                    CONF_CITY_ID: city_id,
                                },
                            )
                    except DiyanetApiError:
                        errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "invalid_city"
            else:
                errors["base"] = "invalid_city"

        return self._show_city_form(errors)

    def _show_city_form(self, errors: dict[str, str]) -> FlowResult:
        """Show the city selection form."""
        city_names = sorted([
            c.get("name") or c.get("cityName") or ""
            for c in self._cities
        ])
        return self.async_show_form(
            step_id="city",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY): vol.In(city_names),
                }
            ),
            errors=errors,
            description_placeholders={
                "country": self._selected_country,
                "state": self._selected_state,
            },
        )
