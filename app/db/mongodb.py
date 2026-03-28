from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.core.config import settings


async def init_db() -> None:
    """Initialise Beanie with all document models."""
    # Import here to avoid circular deps
    from app.models.user import User
    from app.models.hospital import Hospital
    from app.models.ward import Ward
    from app.models.bed import Bed
    from app.models.reservation import Reservation
    from app.models.refresh_token import RefreshToken

    client = AsyncMongoClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB],
        document_models=[User, Hospital, Ward, Bed, Reservation, RefreshToken],
    )
