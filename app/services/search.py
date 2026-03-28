"""
Search service.
Primary flow: MongoDB $near geospatial query → ward filter → availability filter.
LLM (or keyword fallback) extracts structured filters from the free-text query.
"""
import json
import math
from typing import Optional

from app.core.config import settings
from app.models.bed import Bed, BedStatus
from app.models.hospital import Hospital
from app.models.ward import Ward, WardType
from app.schemas.search import SearchFilters, HospitalSearchResult


async def search_hospitals(
    query: str,
    user_lat: float,
    user_lng: float,
    radius_km: Optional[float] = None,
) -> list[HospitalSearchResult]:
    filters = await _parse_query(query)
    if radius_km is not None:
        filters.radius_km = radius_km
    return await _execute_search(filters, user_lat, user_lng)


async def _parse_query(query: str) -> SearchFilters:
    if settings.ANTHROPIC_API_KEY:
        try:
            return await _llm_parse(query)
        except Exception:
            pass
    return _keyword_parse(query)


async def _llm_parse(query: str) -> SearchFilters:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system = (
        "You are a hospital search query parser. "
        "Extract search parameters and return ONLY valid JSON with these fields: "
        'ward_type (one of "ICU","GENERAL","MATERNITY","ER" or null), '
        "emergency (boolean), radius_km (number, default 20), "
        "availability_required (boolean, default true)."
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": query}],
    )
    data = json.loads(message.content[0].text)
    ward_type = data.get("ward_type")
    return SearchFilters(
        ward_type=WardType(ward_type) if ward_type else None,
        emergency=data.get("emergency", False),
        radius_km=float(data.get("radius_km", settings.DEFAULT_SEARCH_RADIUS_KM)),
        availability_required=data.get("availability_required", True),
    )


def _keyword_parse(query: str) -> SearchFilters:
    q = query.lower()
    ward_type: Optional[WardType] = None
    if "icu" in q or "intensive" in q:
        ward_type = WardType.ICU
    elif "matern" in q or "birth" in q or "fertil" in q or "pregnan" in q:
        ward_type = WardType.MATERNITY
    elif "emergency" in q or " er " in q or "urgent" in q:
        ward_type = WardType.ER
    elif "general" in q:
        ward_type = WardType.GENERAL

    return SearchFilters(
        ward_type=ward_type,
        emergency="emergency" in q or "urgent" in q,
        radius_km=settings.DEFAULT_SEARCH_RADIUS_KM,
        availability_required=True,
    )


async def _execute_search(
    filters: SearchFilters,
    user_lat: float,
    user_lng: float,
) -> list[HospitalSearchResult]:
    # ── 1. Geospatial query via MongoDB 2dsphere index ────────────────────────
    # $near returns documents sorted by distance ascending automatically.
    collection = Hospital.get_pymongo_collection()
    max_distance_meters = filters.radius_km * 1000

    raw_hospitals = await collection.find(
        {
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [user_lng, user_lat],  # GeoJSON: [lng, lat]
                    },
                    "$maxDistance": max_distance_meters,
                }
            }
        }
    ).to_list(length=100)

    if not raw_hospitals:
        return []

    results: list[HospitalSearchResult] = []

    for raw in raw_hospitals:
        hospital_id = raw["_id"]
        coords = raw["location"]["coordinates"]
        h_lng, h_lat = coords[0], coords[1]
        distance_km = round(_haversine(user_lat, user_lng, h_lat, h_lng), 2)

        # ── 2. Ward filter ────────────────────────────────────────────────────
        ward_query = Ward.find(Ward.hospital_id == hospital_id)
        if filters.ward_type:
            ward_query = Ward.find(
                Ward.hospital_id == hospital_id,
                Ward.name == filters.ward_type,
            )
        wards = await ward_query.to_list()
        if not wards:
            continue

        # ── 3. Availability filter ────────────────────────────────────────────
        total_available = 0
        ward_summaries = []
        for ward in wards:
            count = await Bed.find(
                Bed.ward_id == ward.id, Bed.status == BedStatus.AVAILABLE
            ).count()
            total_available += count
            ward_summaries.append(
                {"ward_id": str(ward.id), "name": ward.name, "available_beds": count}
            )

        if filters.availability_required and total_available == 0:
            continue

        results.append(
            HospitalSearchResult(
                id=str(hospital_id),
                hospital_name=raw["hospital_name"],
                address=raw["address"],
                lat=h_lat,
                lng=h_lng,
                distance_km=distance_km,
                available_beds=total_available,
                wards=ward_summaries,
            )
        )

    # Already sorted by distance from $near; no secondary sort needed
    return results


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
