from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    database_url: str = "sqlite+pysqlite:///./wenquan.sqlite3"
    web_origin: str = "http://localhost:5173"
    dev_auth_enabled: bool = True
    dev_member_token: str = "dev-member"
    dev_frontdesk_token: str = "dev-frontdesk"
    dev_merchant_token: str = "dev-merchant"
    dev_finance_token: str = "dev-finance"
    dev_admin_token: str = "dev-admin"
    device_service_token: str = "dev-device-service-change-me"
    payment_provider: str = "mock"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
