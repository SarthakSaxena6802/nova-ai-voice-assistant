"""Optional weather service backed by Open-Meteo (free, no API key).

Nova never invents weather data: if the service is disabled, no city is known, or the
network request fails, the user is told exactly that.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("weather")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "foggy", 48: "foggy with rime",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers", 81: "showers",
    82: "violent showers", 85: "snow showers", 86: "heavy snow showers", 95: "a thunderstorm",
    96: "a thunderstorm with hail", 99: "a thunderstorm with heavy hail",
}

_geo_cache: dict[str, dict[str, Any]] = {}


class WeatherError(RuntimeError):
    pass


class WeatherNotConfigured(WeatherError):
    pass


@dataclass
class WeatherReport:
    city: str
    country: str
    day: str
    description: str
    temperature: float | None
    feels_like: float | None
    temp_max: float | None
    temp_min: float | None
    humidity: float | None
    wind_kmh: float | None
    precipitation_probability: float | None
    unit: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def is_enabled() -> bool:
    return get_settings().weather_enabled


def _geocode(client: httpx.Client, city: str) -> dict[str, Any]:
    key = city.lower().strip()
    if key in _geo_cache:
        return _geo_cache[key]
    resp = client.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "en", "format": "json"})
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        raise WeatherError(f"I couldn't find a place called {city}.")
    _geo_cache[key] = results[0]
    return results[0]


def get_weather(city: str, day: str = "today", unit: str = "celsius") -> WeatherReport:
    if not is_enabled():
        raise WeatherNotConfigured("Weather is disabled in the server configuration (NOVA_WEATHER_ENABLED).")
    if not city:
        raise WeatherNotConfigured("I don't know your location yet.")
    timeout = get_settings().weather_timeout_seconds
    try:
        with httpx.Client(timeout=timeout) as client:
            place = _geocode(client, city)
            resp = client.get(
                FORECAST_URL,
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "timezone": "auto",
                    "forecast_days": 2,
                    "temperature_unit": unit,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except WeatherError:
        raise
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("Weather request failed: %s", exc.__class__.__name__)
        raise WeatherError("I couldn't reach the weather service right now. Please check your internet connection.") from exc

    idx = 1 if day == "tomorrow" else 0
    daily = data.get("daily", {})
    current = data.get("current", {}) if idx == 0 else {}

    def pick(key: str) -> Any:
        values = daily.get(key) or []
        return values[idx] if len(values) > idx else None

    code = current.get("weather_code") if idx == 0 and current else pick("weather_code")
    return WeatherReport(
        city=place.get("name", city),
        country=place.get("country", ""),
        day=day,
        description=WMO_CODES.get(code, "unknown conditions"),
        temperature=current.get("temperature_2m"),
        feels_like=current.get("apparent_temperature"),
        temp_max=pick("temperature_2m_max"),
        temp_min=pick("temperature_2m_min"),
        humidity=current.get("relative_humidity_2m"),
        wind_kmh=current.get("wind_speed_10m"),
        precipitation_probability=pick("precipitation_probability_max"),
        unit="°F" if unit == "fahrenheit" else "°C",
    )
