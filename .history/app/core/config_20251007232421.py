from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "dev"
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"

settings = Settings()
