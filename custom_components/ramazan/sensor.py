"""Ramazan entegrasyonu için sensör platformu."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

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
    """Ramazan sensör entity tanımı."""

    value_fn: Callable[[dict[str, Any]], Any] | None = None
    sensor_type: str = ""


def _get_moon_phase_name(url: str | None) -> str:
    """URL'den ay evresi adını çıkarır."""
    if not url:
        return "Bilinmiyor"

    # Görsel dosya adlarını Türkçe ay evresi adlarına eşle
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

    # URL'den uzantısız dosya adını çıkar
    try:
        filename = url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return phase_map.get(filename, filename)
    except (IndexError, AttributeError):
        return "Bilinmiyor"


def _calculate_time_remaining(target_time_str: str | None, tomorrow_time_str: str | None = None) -> str | None:
    """Hedef namaz vaktine kalan süreyi hesaplar.
    
    '2 saat 30 dakika 45 saniye' gibi bir string döner, vakit geçmişse yarının vaktini kullanır.
    """
    if not target_time_str:
        return None

    now = datetime.now()

    try:
        # Bugün için hedef vakti parse et
        hour, minute = map(int, target_time_str.split(":"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Bugünkü vakit geçtiyse yarının vaktini kullan
        if target <= now:
            if tomorrow_time_str:
                hour, minute = map(int, tomorrow_time_str.split(":"))
            target = (now + timedelta(days=1)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

        diff = target - now
        total_secs = int(diff.total_seconds())

        if total_secs <= 0:
            return "Vakit girdi"

        # Saat, dakika ve saniye olarak ayır
        hours = total_secs // 3600
        minutes = (total_secs % 3600) // 60
        seconds = total_secs % 60

        if hours > 0:
            return f"{hours} saat {minutes} dakika {seconds} saniye"
        if minutes > 0:
            return f"{minutes} dakika {seconds} saniye"
        return f"{seconds} saniye"

    except (ValueError, AttributeError):
        return None


def _time_remaining_minutes(target_time_str: str | None, tomorrow_time_str: str | None = None) -> int | None:
    """Hedef namaz vaktine kalan dakikayı tam sayı olarak hesaplar."""
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
        # Saniyeleri yukarı yuvarla — Diyanet uygulaması ile birebir uyum için
        return max(0, math.ceil(diff.total_seconds() / 60))

    except (ValueError, AttributeError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Config entry'den Ramazan sensör entity'lerini kur."""
    coordinator: RamazanDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[RamazanBaseSensor] = []

    # ========================================
    # 1) Namaz vakitleri (sırayla)
    # ========================================

    # 1. İmsak
    entities.append(RamazanPrayerTimeSensor(
        coordinator=coordinator, entry=entry,
        key="fajr",
        name=PRAYER_TIME_SENSORS["fajr"]["name"],
        icon=PRAYER_TIME_SENSORS["fajr"]["icon"],
    ))

    # 2. Güneş
    entities.append(RamazanPrayerTimeSensor(
        coordinator=coordinator, entry=entry,
        key="sunrise",
        name=PRAYER_TIME_SENSORS["sunrise"]["name"],
        icon=PRAYER_TIME_SENSORS["sunrise"]["icon"],
    ))

    # 3. Öğle
    entities.append(RamazanPrayerTimeSensor(
        coordinator=coordinator, entry=entry,
        key="dhuhr",
        name=PRAYER_TIME_SENSORS["dhuhr"]["name"],
        icon=PRAYER_TIME_SENSORS["dhuhr"]["icon"],
    ))

    # 4. İkindi
    entities.append(RamazanPrayerTimeSensor(
        coordinator=coordinator, entry=entry,
        key="asr",
        name=PRAYER_TIME_SENSORS["asr"]["name"],
        icon=PRAYER_TIME_SENSORS["asr"]["icon"],
    ))

    # 5. Akşam
    entities.append(RamazanPrayerTimeSensor(
        coordinator=coordinator, entry=entry,
        key="maghrib",
        name=PRAYER_TIME_SENSORS["maghrib"]["name"],
        icon=PRAYER_TIME_SENSORS["maghrib"]["icon"],
    ))

    # 6. Yatsı
    entities.append(RamazanPrayerTimeSensor(
        coordinator=coordinator, entry=entry,
        key="isha",
        name=PRAYER_TIME_SENSORS["isha"]["name"],
        icon=PRAYER_TIME_SENSORS["isha"]["icon"],
    ))

    # ========================================
    # 2) İftar ve Sahur
    # ========================================

    # 7. İftar (akşam namazı ile aynı)
    entities.append(RamazanPrayerTimeSensor(
        coordinator=coordinator, entry=entry,
        key="maghrib",
        name=EXTRA_SENSORS["iftar"]["name"],
        icon=EXTRA_SENSORS["iftar"]["icon"],
        unique_suffix="iftar",
    ))

    # 8. Sahur (imsak ile aynı)
    entities.append(RamazanPrayerTimeSensor(
        coordinator=coordinator, entry=entry,
        key="fajr",
        name=EXTRA_SENSORS["sahur"]["name"],
        icon=EXTRA_SENSORS["sahur"]["icon"],
        unique_suffix="sahur",
    ))

    # ========================================
    # 3) Geri sayım sensörleri
    # ========================================

    # 9. İftara Kalan Süre
    entities.append(RamazanCountdownSensor(
        coordinator=coordinator, entry=entry,
        target_key="maghrib",
        name=EXTRA_SENSORS["time_to_iftar"]["name"],
        icon=EXTRA_SENSORS["time_to_iftar"]["icon"],
        unique_suffix="time_to_iftar",
    ))

    # 10. Sahura Kalan Süre
    entities.append(RamazanCountdownSensor(
        coordinator=coordinator, entry=entry,
        target_key="fajr",
        name=EXTRA_SENSORS["time_to_sahur"]["name"],
        icon=EXTRA_SENSORS["time_to_sahur"]["icon"],
        unique_suffix="time_to_sahur",
    ))

    # ========================================
    # 4) Ek bilgi sensörleri
    # ========================================

    # 11. Kıble Saati
    entities.append(RamazanInfoSensor(
        coordinator=coordinator, entry=entry,
        data_key="qiblaTime",
        name=EXTRA_SENSORS["qibla_time"]["name"],
        icon=EXTRA_SENSORS["qibla_time"]["icon"],
        unique_suffix="qibla_time",
    ))

    # 12. Hicri Tarih
    entities.append(RamazanInfoSensor(
        coordinator=coordinator, entry=entry,
        data_key="hijriDateLong",
        name=EXTRA_SENSORS["hijri_date"]["name"],
        icon=EXTRA_SENSORS["hijri_date"]["icon"],
        unique_suffix="hijri_date",
    ))

    # 13. Miladi Tarih
    entities.append(RamazanInfoSensor(
        coordinator=coordinator, entry=entry,
        data_key="gregorianDateLong",
        name=EXTRA_SENSORS["gregorian_date"]["name"],
        icon=EXTRA_SENSORS["gregorian_date"]["icon"],
        unique_suffix="gregorian_date",
    ))

    # 14. Astronomik Gün Doğumu
    entities.append(RamazanInfoSensor(
        coordinator=coordinator, entry=entry,
        data_key="astronomicalSunrise",
        name=EXTRA_SENSORS["astronomical_sunrise"]["name"],
        icon=EXTRA_SENSORS["astronomical_sunrise"]["icon"],
        unique_suffix="astronomical_sunrise",
    ))

    # 15. Astronomik Gün Batımı
    entities.append(RamazanInfoSensor(
        coordinator=coordinator, entry=entry,
        data_key="astronomicalSunset",
        name=EXTRA_SENSORS["astronomical_sunset"]["name"],
        icon=EXTRA_SENSORS["astronomical_sunset"]["icon"],
        unique_suffix="astronomical_sunset",
    ))

    # 16. Ay Evresi
    entities.append(RamazanMoonPhaseSensor(
        coordinator=coordinator, entry=entry,
    ))

    async_add_entities(entities)


class RamazanBaseSensor(CoordinatorEntity[RamazanDataUpdateCoordinator], SensorEntity):
    """Ramazan sensörleri için temel sınıf."""

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
        """Sensörü başlat."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Cihaz bilgisini döner."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"Ramazan - {self.coordinator.location_name}",
            manufacturer="Diyanet İşleri Başkanlığı",
            model="Namaz Vakitleri",
        )

    def _get_today_data(self) -> dict[str, Any]:
        """Bugünün namaz vakti verisini döner."""
        if self.coordinator.data:
            return self.coordinator.data.get("today", {}) or {}
        return {}

    def _get_tomorrow_data(self) -> dict[str, Any]:
        """Yarının namaz vakti verisini döner."""
        if self.coordinator.data:
            return self.coordinator.data.get("tomorrow", {}) or {}
        return {}


class RamazanPrayerTimeSensor(RamazanBaseSensor):
    """Namaz vakti sensörü (zaman damgası)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: RamazanDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
        unique_suffix: str | None = None,
    ) -> None:
        """Namaz vakti sensörünü başlat."""
        super().__init__(
            coordinator=coordinator,
            entry=entry,
            name=name,
            icon=icon,
            unique_suffix=unique_suffix or key,
        )
        self._key = key

    @property
    def native_value(self) -> datetime | None:
        """Namaz vaktini datetime olarak döner."""
        data = self._get_today_data()
        time_str = data.get(self._key)
        if not time_str:
            return None

        try:
            # "HH:MM" formatından bugünün tarihiyle datetime oluştur
            hour, minute = map(int, time_str.split(":"))
            now = dt_util.now()
            local_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return local_dt
        except (ValueError, AttributeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ek durum niteliklerini döner."""
        data = self._get_today_data()
        attrs = {}

        # Hicri tarihi nitelik olarak ekle
        hijri = data.get("hijriDateLong")
        if hijri:
            attrs["hicri_tarih"] = hijri

        # Miladi tarihi ekle
        greg = data.get("gregorianDateLong")
        if greg:
            attrs["miladi_tarih"] = greg

        return attrs


class RamazanCountdownSensor(RamazanBaseSensor):
    """İftar/Sahur geri sayım sensörü."""

    def __init__(
        self,
        coordinator: RamazanDataUpdateCoordinator,
        entry: ConfigEntry,
        target_key: str,
        name: str,
        icon: str,
        unique_suffix: str,
    ) -> None:
        """Geri sayım sensörünü başlat."""
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
        """HA'ya eklendiğinde güncelleme zamanlayıcısını kaydet."""
        await super().async_added_to_hass()

        # Saniye gösterimi için her saniye güncelle
        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._async_update_countdown,
            timedelta(seconds=1),
        )

    async def async_will_remove_from_hass(self) -> None:
        """HA'dan kaldırılırken zamanlayıcıyı temizle."""
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _async_update_countdown(self, _now=None) -> None:
        """Geri sayım değerini güncelle."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Geri sayım metnini döner."""
        today_data = self._get_today_data()
        tomorrow_data = self._get_tomorrow_data()

        target_time = today_data.get(self._target_key)
        tomorrow_time = tomorrow_data.get(self._target_key) if tomorrow_data else None

        return _calculate_time_remaining(target_time, tomorrow_time)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Dakika bilgisi dahil ek nitelikleri döner."""
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
    """Ek bilgi sensörü (kıble saati, tarihler vb.)."""

    def __init__(
        self,
        coordinator: RamazanDataUpdateCoordinator,
        entry: ConfigEntry,
        data_key: str,
        name: str,
        icon: str,
        unique_suffix: str,
    ) -> None:
        """Bilgi sensörünü başlat."""
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
        """Sensör değerini döner."""
        data = self._get_today_data()
        return data.get(self._data_key)


class RamazanMoonPhaseSensor(RamazanBaseSensor):
    """Ay evresi sensörü."""

    def __init__(
        self,
        coordinator: RamazanDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Ay evresi sensörünü başlat."""
        super().__init__(
            coordinator=coordinator,
            entry=entry,
            name=EXTRA_SENSORS["moon_phase"]["name"],
            icon=EXTRA_SENSORS["moon_phase"]["icon"],
            unique_suffix="moon_phase",
        )

    @property
    def native_value(self) -> str | None:
        """Ay evresi adını döner."""
        data = self._get_today_data()
        url = data.get("shapeMoonUrl")
        return _get_moon_phase_name(url)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ay görseli URL'sini nitelik olarak döner."""
        data = self._get_today_data()
        attrs = {}
        url = data.get("shapeMoonUrl")
        if url:
            attrs["gorsel_url"] = url
        return attrs
