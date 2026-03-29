from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "dev"

    # DB
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "ksef_user"
    DB_PASS: str = "ksef_password"
    DB_NAME: str = "ksef_db"

    # KSeF
    KSEF_TOKEN: str = ""
    KSEF_NIP: str = ""
    KSEF_BASE_URL: str = ""

    # Encryption (Fernet key: Fernet.generate_key().decode())
    ENCRYPTION_MASTER_KEY: str = ""

    # KSeF sync
    KSEF_SYNC_DATE_FROM: str = "2026-01-01"
    KSEF_EXPORT_POLL_INTERVAL: float = 3.0
    KSEF_EXPORT_TIMEOUT: float = 300.0
    KSEF_DOWNLOAD_DIR: str = "/tmp/ksef_exports"

    @property
    def DATABASE_URL_asyncpg(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
