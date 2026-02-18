"""Sensor platform for Ramazan integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    DOMAIN,
    EXTRA_SENSORS,
    PRAYER_TIME_SENSORS,
)
from .coordinator import RamazanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RamazanSensorEntityDescription(SensorEntityDescription):
    """Describes Ramazan sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any] | None = None
    sensor_type: str = ""


def _get_moon_phase_name(url: str | None) -> str:
    """Extract moon phase name from URL."""
    if not url:
        return "Bilinmiyor"

    # Map image filenames to Turkish moon phase names
    phase_map = {
        "ictima": "İçtima (Yeni Ay)",
        "ruyet": "Hilal (Rüyet)",
        "r1": "Hilal (1. Gün)",
        "r2": "Hilal (2. Gün)",
        "r3": "Hilal (3. Gün)",
        "r4": "Hilal (4. Gün)",
        "r5": "Hilal (5. Gün)",
        "ilkdordun": "İlk Dördün",
        "i1": "İlk Dördün (1. Gün)",
        "i2": "İlk Dördün (2. Gün)",
        "i3": "İlk Dördün (3. Gün)",
        "i4": "İlk Dördün (4. Gün)",
        "i5": "İlk Dördün (5. Gün)",
        "i6": "İlk Dördün (6. Gün)",
        "dolunay": "Dolunay",
        "d1": "Dolunay (1. Gün)",
        "d2": "Dolunay (2. Gün)",
        "d3": "Dolunay (3. Gün)",
        "d4": "Dolunay (4. Gün)",
        "d5": "Dolunay (5. Gün)",
        "d6": "Dolunay (6. Gün)",
        "d7": "Dolunay (7. Gün)",
        "sondordun": "Son Dördün",
        "sd1": "Son Dördün (1. Gün)",
        "sd2": "Son Dördün (2. Gün)",
        "sd3": "Son Dördün (3. Gün)",
        "sd4": "Son Dördün (4. Gün)",
        "sd5": "Son Dördün (5. Gün)",
        "sd6": "Son Dördün (6. Gün)",
        "sd7": "Son Dördün (7. Gün)",
    }

    # Extract filename without extension from URL
    try:
        filename = url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return phase_map.get(filename, filename)
    except (IndexError, AttributeError):
        return "Bilinmiyor"


def _calculate_time_remaining(target_time_str: str | None, tomorrow_time_str: str | None = None) -> str | None:
    """Calculate remaining time to a target prayer time.
    
    Returns a string like '2 saat 30 dakika' or None if target has passed.
    """
    if not target_time_str:
        return None

    now = datetime.now()

    try:
        # Parse target time for today
        hour, minute = map(int, target_time_str.split(":"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If target time has passed today, use tomorrow's time
        if target <= now:
            if tomorrow_time_str:
                hour, minute = map(int, tomorrow_time_str.split(":"))
            target = (now + timedelta(days=1)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

        diff = target - now
        total_seconds = int(diff.total_seconds())

        if total_seconds <= 0:
            return "Vakit girdi"

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours} saat {minutes} dakika"
        return f"{minutes} dakika"

    except (ValueError, AttributeError):
        return None


def _time_remaining_minutes(target_time_str: str | None, tomorrow_time_str: str | None = None) -> int | None:
    """Calculate remaining minutes to a target prayer time as integer."""
    if not target_time_str:
        return None

    now = datetime.now()

    try:
        hour, minute = map(int, target_time_str.split(":"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if target <= now:
            if tomorrow_time_str:
                hour, minute = map(int, tomorrow_time_str.split(":"))
            target = (now + timedelta(days=1)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

        diff = target - now
        return max(0, int(diff.total_seconds()) // 60)

    except (ValueError, AttributeError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ramazan sensor entities from a config entry."""
    coordinator: RamazanDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[RamazanSensor] = []

    # Prayer time sensors
    for key, config in PRAYER_TIME_SENSORS.items():
        entities.append(
            RamazanPrayerTimeSensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                name=config["name"],
                icon=config["icon"],
            )
        )

    # Iftar sensor (same as maghrib)
    entities.append(
        RamazanPrayerTimeSensor(
            coordinator=coordinator,
            entry=entry,
            key="maghrib",
            name=EXTRA_SENSORS["iftar"]["name"],
            icon=EXTRA_SENSORS["iftar"]["icon"],
            unique_suffix="iftar",
        )
    )

    # Sahur sensor (same as fajr)
    entities.append(
        RamazanPrayerTimeSensor(
            coordinator=coordinator,
            entry=entry,
            key="fajr",
            name=EXTRA_SENSORS["sahur"]["name"],
            icon=EXTRA_SENSORS["sahur"]["icon"],
            unique_suffix="sahur",
        )
    )

    # Countdown sensors
    entities.append(
        RamazanCountdownSensor(
            coordinator=coordinator,
            entry=entry,
            target_key="maghrib",
            name=EXTRA_SENSORS["time_to_iftar"]["name"],
            icon=EXTRA_SENSORS["time_to_iftar"]["icon"],
            unique_suffix="time_to_iftar",
        )
    )

    entities.append(
        RamazanCountdownSensor(
            coordinator=coordinator,
            entry=entry,
            target_key="fajr",
            name=EXTRA_SENSORS["time_to_sahur"]["name"],
            icon=EXTRA_SENSORS["time_to_sahur"]["icon"],
            unique_suffix="time_to_sahur",
        )
    )

    # Extra info sensors
    entities.append(
        RamazanInfoSensor(
            coordinator=coordinator,
            entry=entry,
            data_key="qiblaTime",
            name=EXTRA_SENSORS["qibla_time"]["name"],
            icon=EXTRA_SENSORS["qibla_time"]["icon"],
            unique_suffix="qibla_time",
        )
    )

    entities.append(
        RamazanInfoSensor(
            coordinator=coordinator,
            entry=entry,
            data_key="hijriDateLong",
            name=EXTRA_SENSORS["hijri_date"]["name"],
            icon=EXTRA_SENSORS["hijri_date"]["icon"],
            unique_suffix="hijri_date",
        )
    )

    entities.append(
        RamazanInfoSensor(
            coordinator=coordinator,
            entry=entry,
            data_key="gregorianDateLong",
            name=EXTRA_SENSORS["gregorian_date"]["name"],
            icon=EXTRA_SENSORS["gregorian_date"]["icon"],
            unique_suffix="gregorian_date",
        )
    )

    entities.append(
        RamazanInfoSensor(
            coordinator=coordinator,
            entry=entry,
            data_key="astronomicalSunrise",
            name=EXTRA_SENSORS["astronomical_sunrise"]["name"],
            icon=EXTRA_SENSORS["astronomical_sunrise"]["icon"],
            unique_suffix="astronomical_sunrise",
        )
    )

    entities.append(
        RamazanInfoSensor(
            coordinator=coordinator,
            entry=entry,
            data_key="astronomicalSunset",
            name=EXTRA_SENSORS["astronomical_sunset"]["name"],
            icon=EXTRA_SENSORS["astronomical_sunset"]["icon"],
            unique_suffix="astronomical_sunset",
        )
    )

    # Moon phase sensor
    entities.append(
        RamazanMoonPhaseSensor(
            coordinator=coordinator,
            entry=entry,
        )
    )

    async_add_entities(entities)


class RamazanBaseSensor(CoordinatorEntity[RamazanDataUpdateCoordinator], SensorEntity):
    """Base class for Ramazan sensors."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: RamazanDataUpdateCoordinator,
        entry: ConfigEntry,
        name: str,
        icon: str,
        unique_suffix: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"Ramazan - {self.coordinator.location_name}",
            manufacturer="Diyanet İşleri Başkanlığı",
            model="Namaz Vakitleri",
        )

    def _get_today_data(self) -> dict[str, Any]:
        """Get today's prayer data."""
        if self.coordinator.data:
            return self.coordinator.data.get("today", {}) or {}
        return {}

    def _get_tomorrow_data(self) -> dict[str, Any]:
        """Get tomorrow's prayer data."""
        if self.coordinator.data:
            return self.coordinator.data.get("tomorrow", {}) or {}
        return {}


class RamazanPrayerTimeSensor(RamazanBaseSensor):
    """Sensor for individual prayer times."""

    def __init__(
        self,
        coordinator: RamazanDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
        unique_suffix: str | None = None,
    ) -> None:
        """Initialize the prayer time sensor."""
        super().__init__(
            coordinator=coordinator,
            entry=entry,
            name=name,
            icon=icon,
            unique_suffix=unique_suffix or key,
        )
        self._key = key

    @property
    def native_value(self) -> str | None:
        """Return the prayer time."""
        data = self._get_today_data()
        return data.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self._get_today_data()
        attrs = {}

        # Add Hijri date as an attribute
        hijri = data.get("hijriDateLong")
        if hijri:
            attrs["hicri_tarih"] = hijri

        # Add Gregorian date
        greg = data.get("gregorianDateLong")
        if greg:
            attrs["miladi_tarih"] = greg

        return attrs


class RamazanCountdownSensor(RamazanBaseSensor):
    """Sensor for countdown to iftar/sahur."""

    def __init__(
        self,
        coordinator: RamazanDataUpdateCoordinator,
        entry: ConfigEntry,
        target_key: str,
        name: str,
        icon: str,
        unique_suffix: str,
    ) -> None:
        """Initialize the countdown sensor."""
        super().__init__(
            coordinator=coordinator,
            entry=entry,
            name=name,
            icon=icon,
            unique_suffix=unique_suffix,
        )
        self._target_key = target_key
        self._unsub_timer = None

    async def async_added_to_hass(self) -> None:
        """Register update interval when added to hass."""
        await super().async_added_to_hass()

        # Update every minute for countdown accuracy
        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._async_update_countdown,
            timedelta(minutes=1),
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister update interval."""
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _async_update_countdown(self, _now=None) -> None:
        """Update the countdown value."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the countdown string."""
        today_data = self._get_today_data()
        tomorrow_data = self._get_tomorrow_data()

        target_time = today_data.get(self._target_key)
        tomorrow_time = tomorrow_data.get(self._target_key) if tomorrow_data else None

        return _calculate_time_remaining(target_time, tomorrow_time)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes including minutes."""
        today_data = self._get_today_data()
        tomorrow_data = self._get_tomorrow_data()

        target_time = today_data.get(self._target_key)
        tomorrow_time = tomorrow_data.get(self._target_key) if tomorrow_data else None

        attrs = {}
        minutes = _time_remaining_minutes(target_time, tomorrow_time)
        if minutes is not None:
            attrs["kalan_dakika"] = minutes
            attrs["kalan_saat"] = round(minutes / 60, 1)

        if target_time:
            attrs["hedef_vakit"] = target_time

        return attrs


class RamazanInfoSensor(RamazanBaseSensor):
    """Sensor for extra information (qibla time, dates, etc.)."""

    def __init__(
        self,
        coordinator: RamazanDataUpdateCoordinator,
        entry: ConfigEntry,
        data_key: str,
        name: str,
        icon: str,
        unique_suffix: str,
    ) -> None:
        """Initialize the info sensor."""
        super().__init__(
            coordinator=coordinator,
            entry=entry,
            name=name,
            icon=icon,
            unique_suffix=unique_suffix,
        )
        self._data_key = data_key

    @property
    def native_value(self) -> str | None:
        """Return the sensor value."""
        data = self._get_today_data()
        return data.get(self._data_key)


class RamazanMoonPhaseSensor(RamazanBaseSensor):
    """Sensor for moon phase."""

    def __init__(
        self,
        coordinator: RamazanDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the moon phase sensor."""
        super().__init__(
            coordinator=coordinator,
            entry=entry,
            name=EXTRA_SENSORS["moon_phase"]["name"],
            icon=EXTRA_SENSORS["moon_phase"]["icon"],
            unique_suffix="moon_phase",
        )

    @property
    def native_value(self) -> str | None:
        """Return the moon phase name."""
        data = self._get_today_data()
        url = data.get("shapeMoonUrl")
        return _get_moon_phase_name(url)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return moon image URL as attribute."""
        data = self._get_today_data()
        attrs = {}
        url = data.get("shapeMoonUrl")
        if url:
            attrs["gorsel_url"] = url
        return attrs
