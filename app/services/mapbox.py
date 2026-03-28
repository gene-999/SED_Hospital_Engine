"""
Mapbox Directions API client.
Returns driving duration in seconds between two coordinates.
"""
from typing import Optional

import httpx

from app.core.config import settings

DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving/{coords}"


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
