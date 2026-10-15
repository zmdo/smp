from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    internal_token: str
    encryption_key: str | None = None
    encryption_key_file: str = "/data/fernet.key"
    inspect_interval_seconds: int = 30


settings = Settings()
