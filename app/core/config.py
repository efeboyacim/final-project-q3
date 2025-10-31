# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DB
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "app"
    db_user: str = "postgres"
    db_password: str = "postgres"

    # JWT
    secret_key: str = "devsecret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

settings: Settings = Settings()
