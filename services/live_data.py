import os
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

NEW_DELHI = {"lat": 28.6139, "lon": 77.2090, "name": "New Delhi"}
CACHE = {}


def _cached(key, ttl_seconds, loader):
    now = time.time()
    item = CACHE.get(key)
    if item and now - item["time"] < ttl_seconds:
        return item["data"]
    data = loader()
    CACHE[key] = {"time": now, "data": data}
    return data


def _get_json(url, params=None, timeout=8):
    headers = {"User-Agent": "SECTORIQ-AI/1.0 (hackathon prototype)"}
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def weather(lat=None, lon=None):
    lat = lat if lat is not None else NEW_DELHI["lat"]
    lon = lon if lon is not None else NEW_DELHI["lon"]

    def load():
        data = _get_json(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                "forecast_days": 7,
                "timezone": "Asia/Kolkata",
            },
        )
        current = data.get("current", {})
        daily = data.get("daily", {})
        return {
            "source": "Open-Meteo",
            "location": {"name": NEW_DELHI["name"], "latitude": lat, "longitude": lon},
            "time": current.get("time"),
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "wind_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
            "daily": daily,
        }

    return _cached(f"weather:{lat}:{lon}", 300, load)


def holidays(year=None):
    year = year or datetime.now().year

    def load():
        data = _get_json(f"https://date.nager.at/api/v3/PublicHolidays/{year}/IN")
        return [
            {
                "name": h.get("localName") or h.get("name"),
                "date": h.get("date"),
                "event_type": "Festival/Holiday",
                "impact_level": "High" if h.get("global") else "Medium",
                "source": "Nager.Date",
                "latitude": NEW_DELHI["lat"],
                "longitude": NEW_DELHI["lon"],
            }
            for h in data
        ]

    return _cached(f"holidays:{year}", 21600, load)


def google_calendar_events():
    api_key = os.getenv("GOOGLE_CALENDAR_API_KEY", "").strip()
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "").strip()
    if not api_key or not calendar_id:
        return []

    now = datetime.now(timezone.utc)
    time_min = now.isoformat().replace("+00:00", "Z")
    time_max = (now + timedelta(days=120)).isoformat().replace("+00:00", "Z")

    def load():
        data = _get_json(
            f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id, safe='')}/events",
            params={
                "key": api_key,
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": 50,
            },
        )
        results = []
        for item in data.get("items", []):
            start = item.get("start", {})
            date = start.get("date") or (start.get("dateTime", "")[:10] if start.get("dateTime") else None)
            if not date:
                continue
            results.append({
                "name": item.get("summary", "Calendar Event"),
                "date": date,
                "event_type": "Calendar Event",
                "impact_level": "Medium",
                "source": "Google Calendar",
                "latitude": NEW_DELHI["lat"],
                "longitude": NEW_DELHI["lon"],
            })
        return results

    return _cached("google_calendar", 300, load)


def ticketmaster_events():
    api_key = os.getenv("TICKETMASTER_API_KEY", "").strip()
    if not api_key:
        return []

    def load():
        data = _get_json(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params={
                "apikey": api_key,
                "latlong": f"{NEW_DELHI['lat']},{NEW_DELHI['lon']}",
                "radius": 50,
                "unit": "km",
                "size": 30,
                "sort": "date,asc",
            },
        )
        results = []
        for item in data.get("_embedded", {}).get("events", []):
            start = item.get("dates", {}).get("start", {})
            date = start.get("localDate")
            venue = (item.get("_embedded", {}).get("venues") or [{}])[0]
            loc = venue.get("location", {})
            if not date:
                continue
            results.append({
                "name": item.get("name", "Event"),
                "date": date,
                "event_type": "Live Event",
                "impact_level": "High",
                "source": "Ticketmaster",
                "latitude": float(loc.get("latitude", NEW_DELHI["lat"])),
                "longitude": float(loc.get("longitude", NEW_DELHI["lon"])),
                "url": item.get("url"),
                "venue": venue.get("name"),
            })
        return results

    return _cached("ticketmaster", 300, load)


def live_events(local_events):
    today = datetime.now().date().isoformat()
    external = []
    errors = []

    for name, fn in (("holidays", holidays), ("google_calendar", google_calendar_events), ("ticketmaster", ticketmaster_events)):
        try:
            external.extend(fn())
        except Exception as exc:
            errors.append({"source": name, "error": str(exc)})

    merged = {}
    for event in external:
        key = (event["name"].strip().lower(), event["date"])
        merged[key] = event

    # Local database events remain available as a fallback and are explicitly marked.
    for event in local_events:
        key = (event["name"].strip().lower(), event["date"])
        if key not in merged:
            item = dict(event)
            item["source"] = item.get("source", "Local database")
            merged[key] = item

    events = sorted(merged.values(), key=lambda x: x.get("date", ""))
    return {
        "events": events,
        "sources": sorted(set(e.get("source", "Unknown") for e in events)),
        "errors": errors,
        "as_of": datetime.now().astimezone().isoformat(),
        "today": today,
    }


def live_status():
    return {
        "server_time": datetime.now().astimezone().isoformat(),
        "weather": "Open-Meteo",
        "holidays": "Nager.Date",
        "google_calendar_enabled": bool(os.getenv("GOOGLE_CALENDAR_API_KEY") and os.getenv("GOOGLE_CALENDAR_ID")),
        "ticketmaster_enabled": bool(os.getenv("TICKETMASTER_API_KEY")),
        "refresh_seconds": 300,
    }
