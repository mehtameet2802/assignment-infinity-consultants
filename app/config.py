from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./spend_tracker.db"
    auth_enabled: bool = Field(default=False, validation_alias="AUTH_ENABLED")
    api_key_pepper: str | None = Field(default=None, validation_alias="API_KEY_PEPPER")
    admin_password_hash: str | None = Field(
        default=None, validation_alias="ADMIN_PASSWORD_HASH"
    )


settings = Settings()
