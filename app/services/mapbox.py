"""
Mapbox API client.
- Directions: driving duration in seconds between two coordinates.
- Geocoding: convert a free-text location description to (lat, lng).
"""
from typing import Optional

import httpx

from app.core.config import settings

DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving/{coords}"
GEOCODING_URL = "https://api.mapbox.com/search/geocode/v6/forward"


async def get_driving_duration_seconds(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
) -> Optional[float]:
    """
    Returns driving duration in seconds, or None if unavailable.
    Mapbox coordinates are [longitude, latitude].
    """
    if not settings.MAPBOX_ACCESS_TOKEN:
        return None

    coords = f"{from_lng},{from_lat};{to_lng},{to_lat}"
    url = DIRECTIONS_URL.format(coords=coords)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                params={
                    "access_token": settings.MAPBOX_ACCESS_TOKEN,
                    "overview": "false",
                    "steps": "false",
                },
            )
            r.raise_for_status()
            data = r.json()
            routes = data.get("routes", [])
            if not routes:
                return None
            # Return the longest route duration so we don't underestimate
            return max(route["duration"] for route in routes)
    except Exception:
        return None


async def geocode_location(description: str) -> Optional[tuple[float, float]]:
    """
    Convert a free-text location description to (lat, lng).
    Returns None if geocoding fails or no token is configured.
    """
    if not settings.MAPBOX_ACCESS_TOKEN:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                GEOCODING_URL,
                params={
                    "q": description,
                    "access_token": settings.MAPBOX_ACCESS_TOKEN,
                    "limit": 1,
                },
            )
            r.raise_for_status()
            data = r.json()
            features = data.get("features", [])
            if not features:
                return None
            coords = features[0]["geometry"]["coordinates"]  # [lng, lat]
            return coords[1], coords[0]  # (lat, lng)
    except Exception:
        return None
