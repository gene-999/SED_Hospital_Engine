from fastapi import APIRouter

from app.schemas.search import SearchRequest, HospitalSearchResult
from app.services import search as search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=list[HospitalSearchResult])
async def search(data: SearchRequest) -> list[HospitalSearchResult]:
    return await search_service.search_hospitals(
        data.query, data.user_lat, data.user_lng, data.radius_km
    )
