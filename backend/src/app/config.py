from functools import lru_cache
from os import getenv


class Settings:
    def __init__(self) -> None:
        self.database_url = getenv("DATABASE_URL", "sqlite:///./auth.db")
        self.jwt_secret = getenv("JWT_SECRET", "dev-secret-change-me")
        self.jwt_algorithm = getenv("JWT_ALGORITHM", "HS256")
        self.access_token_ttl_seconds = int(getenv("ACCESS_TOKEN_TTL_SECONDS", "900"))
        self.refresh_token_ttl_seconds = int(
            getenv("REFRESH_TOKEN_TTL_SECONDS", "604800")
        )
        self.refresh_cookie_name = getenv("REFRESH_COOKIE_NAME", "refresh_token")
        self.refresh_cookie_secure = (
            getenv("REFRESH_COOKIE_SECURE", "true").lower() == "true"
        )
        self.refresh_cookie_httponly = (
            getenv("REFRESH_COOKIE_HTTPONLY", "true").lower() == "true"
        )
        self.refresh_cookie_samesite = getenv("REFRESH_COOKIE_SAMESITE", "strict")
        self.max_upload_size_bytes = int(
            getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024))
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
