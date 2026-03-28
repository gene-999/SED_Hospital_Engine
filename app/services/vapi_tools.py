"""
Business logic for VAPI voice-agent tools.

Tool 1 — find_nearby_hospitals
  Input:  location_description (text), radius_km (optional)
  Flow:   Mapbox geocode → MongoDB $near → return hospitals with ward summaries
  Output: list of hospitals with id, name, address, distance, available wards

Tool 2 — filter_by_condition
  Input:  hospital_ids (from prior tool call), condition_description (text)
  Flow:   LLM/keyword maps condition → ward type → filter each hospital's wards
  Output: narrowed list of hospitals + matching wards that have available beds
"""
import json
from typing import Optional

from app.core.config import settings
from app.models.bed import Bed, BedStatus
from app.models.hospital import Hospital
from app.models.ward import Ward, WardType
from app.services.mapbox import geocode_location


# ── Tool 1 ────────────────────────────────────────────────────────────────────

async def find_nearby_hospitals(
    location_description: str,
    radius_km: float = 20.0,
) -> dict:
    """
    Geocode the location description then run a MongoDB $near query.
    Returns hospitals within radius_km that have at least one available bed.
    """
    coords = await geocode_location(location_description)
    if coords is None:
        return {
            "error": (
                f"Could not determine coordinates for '{location_description}'. "
                "Please ask the patient to describe their location more specifically, "
                "e.g. a landmark, street, or neighbourhood."
            )
        }

    lat, lng = coords
    collection = Hospital.get_pymongo_collection()
    max_meters = radius_km * 1000

    raw_hospitals = await collection.find(
        {
            "location": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                    "$maxDistance": max_meters,
                }
            }
        }
    ).to_list(length=50)

    if not raw_hospitals:
        return {
            "hospitals": [],
            "message": (
                f"No hospitals found within {radius_km} km of '{location_description}'. "
                "You may want to ask the patient if they can travel further."
            ),
            "geocoded_location": {"lat": lat, "lng": lng},
        }

    hospitals_out = []
    import math

    for raw in raw_hospitals:
        h_id = str(raw["_id"])
        coords_h = raw["location"]["coordinates"]
        h_lng, h_lat = coords_h[0], coords_h[1]

        # Distance
        R = 6371.0
        dphi = math.radians(h_lat - lat)
        dlambda = math.radians(h_lng - lng)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(math.radians(lat))
            * math.cos(math.radians(h_lat))
            * math.sin(dlambda / 2) ** 2
        )
        distance_km = round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

        # Aggregate ward availability
        wards = await Ward.find(Ward.hospital_id == raw["_id"]).to_list()
        ward_summaries = []
        total_available = 0
        for ward in wards:
            count = await Bed.find(
                Bed.ward_id == ward.id, Bed.status == BedStatus.AVAILABLE
            ).count()
            total_available += count
            if count > 0:
                ward_summaries.append({"ward_type": ward.name, "available_beds": count})

        if total_available == 0:
            continue  # skip hospitals with no available beds

        hospitals_out.append(
            {
                "hospital_id": h_id,
                "name": raw["hospital_name"],
                "address": raw.get("address", ""),
                "distance_km": distance_km,
                "total_available_beds": total_available,
                "wards": ward_summaries,
            }
        )

    return {
        "hospitals": hospitals_out,
        "geocoded_location": {"lat": lat, "lng": lng},
        "count": len(hospitals_out),
    }


# ── Tool 2 ────────────────────────────────────────────────────────────────────

async def filter_by_condition(
    condition_description: str,
    hospital_ids: list[str],
) -> dict:
    """
    Map the condition description to a ward type (via LLM or keyword),
    then filter the provided hospital list to those wards with available beds.
    """
    ward_type = await _map_condition_to_ward(condition_description)

    results = []
    for h_id in hospital_ids:
        hospital = await Hospital.get(h_id)
        if not hospital:
            continue

        ward_query = Ward.find(Ward.hospital_id == hospital.id)
        if ward_type:
            ward_query = Ward.find(
                Ward.hospital_id == hospital.id,
                Ward.name == ward_type,
            )
        wards = await ward_query.to_list()

        matching_wards = []
        for ward in wards:
            count = await Bed.find(
                Bed.ward_id == ward.id, Bed.status == BedStatus.AVAILABLE
            ).count()
            if count > 0:
                matching_wards.append({"ward_id": str(ward.id), "ward_type": ward.name, "available_beds": count})

        if matching_wards:
            results.append(
                {
                    "hospital_id": h_id,
                    "name": hospital.hospital_name,
                    "address": hospital.address,
                    "matching_wards": matching_wards,
                }
            )

    if not results:
        ward_label = ward_type or "any ward type"
        return {
            "hospitals": [],
            "matched_ward_type": ward_type,
            "message": (
                f"No hospitals in the shortlist have available beds for '{condition_description}' "
                f"(matched to: {ward_label}). Consider expanding the search radius."
            ),
        }

    return {
        "hospitals": results,
        "matched_ward_type": ward_type,
        "count": len(results),
    }


async def _map_condition_to_ward(condition: str) -> Optional[str]:
    """
    Map a free-text condition to a WardType value.
    Uses LLM if ANTHROPIC_API_KEY is set, otherwise keyword matching.
    Returns None if no specific ward type can be determined (match all).
    """
    if settings.ANTHROPIC_API_KEY:
        try:
            return await _llm_map_condition(condition)
        except Exception:
            pass
    return _keyword_map_condition(condition)


async def _llm_map_condition(condition: str) -> Optional[str]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=64,
        system=(
            "You map patient conditions to hospital ward types. "
            'Reply with ONLY one of: "ICU", "GENERAL", "MATERNITY", "ER", or "null". '
            "ICU: life-threatening, needs intensive monitoring. "
            "ER: emergency/urgent but not necessarily ICU. "
            "MATERNITY: pregnancy, childbirth, fertility. "
            "GENERAL: routine, non-emergency. "
            'Reply "null" if unclear.'
        ),
        messages=[{"role": "user", "content": condition}],
    )
    raw = message.content[0].text.strip().strip('"')
    if raw == "null":
        return None
    if raw in WardType.__members__:
        return raw
    return None


def _keyword_map_condition(condition: str) -> Optional[str]:
    c = condition.lower()
    if any(w in c for w in ["icu", "intensive", "critical", "ventilat", "coma", "unconscious", "life support"]):
        return WardType.ICU
    if any(w in c for w in ["pregnant", "birth", "labour", "labor", "matern", "fertil", "antenatal", "postnatal", "midwif"]):
        return WardType.MATERNITY
    if any(w in c for w in ["emergency", "urgent", "accident", "trauma", "fracture", "bleeding", "chest pain", "stroke", "seizure"]):
        return WardType.ER
    if any(w in c for w in ["general", "routine", "checkup", "recovery", "observation", "ward"]):
        return WardType.GENERAL
    return None
