"""Constants for the Ramazan integration."""
from __future__ import annotations

DOMAIN = "ramazan"

# API Configuration
API_BASE_URL = "https://t061.diyanet.gov.tr"
API_AUTH_ENDPOINT = "/auth/jwt"
API_PRAYER_TIMES_ENDPOINT = "/apigateway/awqatsalah/api/PrayerTime/Monthly"
API_COUNTRIES_ENDPOINT = "/apigateway/awqatsalah/api/Place/Countries"
API_STATES_ENDPOINT = "/apigateway/awqatsalah/api/Place/States"
API_CITIES_ENDPOINT = "/apigateway/awqatsalah/api/Place/Cities"

# Auth credentials
API_CLIENT_ID = "3e28dc25-54e7-4b8d-a14a-254e97f40b81"
API_CLIENT_SECRET = "-"
API_USERNAME = "DIYANET-MOBIL-001"
API_PASSWORD = "RMQqpfX42K7HCNs9"

# Update interval in seconds (6 hours - prayer times change daily, no need for frequent updates)
UPDATE_INTERVAL = 21600

# Configuration keys
CONF_COUNTRY = "country"
CONF_COUNTRY_ID = "country_id"
CONF_STATE = "state"
CONF_STATE_ID = "state_id"
CONF_CITY = "city"
CONF_CITY_ID = "city_id"

# Platforms
PLATFORMS = ["sensor"]

# Attribution
ATTRIBUTION = "Veriler: T.C. Diyanet İşleri Başkanlığı"

# Sensor definitions
PRAYER_TIME_SENSORS = {
    "fajr": {
        "name": "İmsak",
        "icon": "mdi:weather-sunset-up",
    },
    "sunrise": {
        "name": "Güneş",
        "icon": "mdi:weather-sunny",
    },
    "dhuhr": {
        "name": "Öğle",
        "icon": "mdi:weather-sunny",
    },
    "asr": {
        "name": "İkindi",
        "icon": "mdi:weather-sunny",
    },
    "maghrib": {
        "name": "Akşam",
        "icon": "mdi:weather-sunset-down",
    },
    "isha": {
        "name": "Yatsı",
        "icon": "mdi:weather-night",
    },
}

EXTRA_SENSORS = {
    "iftar": {
        "name": "İftar",
        "icon": "mdi:food-halal",
    },
    "sahur": {
        "name": "Sahur",
        "icon": "mdi:food-halal",
    },
    "time_to_iftar": {
        "name": "İftara Kalan Süre",
        "icon": "mdi:timer-sand",
    },
    "time_to_sahur": {
        "name": "Sahura Kalan Süre",
        "icon": "mdi:timer-sand",
    },
    "qibla_time": {
        "name": "Kıble Saati",
        "icon": "mdi:compass-rose",
    },
    "hijri_date": {
        "name": "Hicri Tarih",
        "icon": "mdi:calendar-star",
    },
    "gregorian_date": {
        "name": "Miladi Tarih",
        "icon": "mdi:calendar",
    },
    "astronomical_sunrise": {
        "name": "Astronomik Gün Doğumu",
        "icon": "mdi:weather-sunset-up",
    },
    "astronomical_sunset": {
        "name": "Astronomik Gün Batımı",
        "icon": "mdi:weather-sunset-down",
    },
    "moon_phase": {
        "name": "Ay Evresi",
        "icon": "mdi:moon-waning-crescent",
    },
}
