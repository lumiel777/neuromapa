import time

import httpx

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 30 * 60
TIMEZONE = "America/Argentina/Cordoba"

_cache = {}


def _key(lat, lon):
    return round(lat, 2), round(lon, 2)


def get_forecast(lat, lon, client=None):
    key = _key(lat, lon)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    params = {"latitude": lat, "longitude": lon, "timezone": TIMEZONE,
              "daily": "temperature_2m_max,precipitation_sum,wind_speed_10m_max,weather_code"}
    response = (client or httpx).get(OPEN_METEO, params=params, timeout=8)
    response.raise_for_status()
    forecast = parse(response.json())
    _cache[key] = (time.time(), forecast)
    return forecast


def parse(payload):
    daily = payload["daily"]
    return {
        "max_temp_c": daily["temperature_2m_max"][0],
        "rain_mm": daily["precipitation_sum"][0],
        "wind_kmh": daily["wind_speed_10m_max"][0],
        "storm": daily["weather_code"][0] >= 95,
    }
