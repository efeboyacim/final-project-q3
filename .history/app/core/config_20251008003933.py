from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")  # fazlalıkları yok say

    app_env: str | None = None  # APP_ENV için
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    @property
    def sqlalchemy_url(self) -> str:
        return f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()
