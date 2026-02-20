"""The Ramazan integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .coordinator import RamazanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS_LIST: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ramazan from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = RamazanDataUpdateCoordinator(hass, entry)

    # Attempt first refresh but don't let a temporary API failure prevent setup.
    # Sensors will show 'unavailable' until the next successful poll if API is down.
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as err:
        _LOGGER.warning(
            "Ramazan: Could not fetch initial data (%s). "
            "Integration will continue and retry automatically.",
            err,
        )
        # Schedule a background refresh rather than blocking setup
        coordinator.async_set_updated_data({})
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Ramazan: Unexpected error during initial data fetch (%s). "
            "Integration will continue and retry automatically.",
            err,
        )
        coordinator.async_set_updated_data({})

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_LIST)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS_LIST):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
