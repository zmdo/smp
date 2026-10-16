from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    ops_url: str = "http://ops:8081"
    internal_token: str
    session_secret: str
    admin_username: str = "admin"
    admin_password: str
    wallet_deriver_node: str = "node"
    wallet_deriver_script: str = ""


settings = Settings()
