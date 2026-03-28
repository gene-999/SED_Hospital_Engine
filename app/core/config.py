from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Bed-Ready"
    DEBUG: bool = False

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "bedready"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Anthropic (optional — enables LLM-powered search query parsing)
    ANTHROPIC_API_KEY: str = ""

    # Mapbox (required for ETA-based reservation expiry)
    MAPBOX_ACCESS_TOKEN: str = ""

    # Fallback expiry added to Mapbox driving ETA (minutes)
    EXPIRY_BUFFER_MINUTES: int = 20

    # Fallback when Mapbox unavailable (minutes)
    EXPIRY_FALLBACK_MINUTES: int = 40

    # Initial search radius (km)
    DEFAULT_SEARCH_RADIUS_KM: float = 20.0


settings = Settings()
