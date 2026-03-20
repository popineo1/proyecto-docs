from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SaaS Platform API"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str
    SECRET_KEY: str

    # Supabase Configuration
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()  # type: ignore