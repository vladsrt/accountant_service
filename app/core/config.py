from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Constant — project root (same as former src/config.PROJECT_ROOT)
PROJECT_ROOT = Path(__file__).parent.parent.parent


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
    KSEF_EXPORT_POLL_INTERVAL: float = 3.0
    KSEF_EXPORT_TIMEOUT: float = 300.0
    KSEF_DOWNLOAD_DIR: str = "/tmp/ksef_exports"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth & JWT
    SECRET_KEY: str = "supersecret_dev_key_replace_in_prod"
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Classification pipeline (merged from src/config.py) ---
    OPENAI_API_KEY: str = ""
    FRONT_DESK_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.0
    GREEN_CORRIDOR_THRESHOLD: float = 0.90

    VALID_RATES: set[float] = {2, 3, 5.5, 8.5, 10, 12, 12.5, 14, 15, 17}

    FATAL_AMBIGUITIES: set[str] = {"alcohol_threshold_unknown"}

    THRESHOLD_PKWIU_PREFIXES: tuple[str, ...] = (
        "55",
        "72",
        "77.11.10.0",
        "77.12.1",
        "77.34.10.0",
        "77.35.10.0",
        "77.39.11.0",
        "77.39.12.0",
        "77.39.13.0",
        "87",
    )
    REVENUE_THRESHOLD: int = 100_000

    NULL_PKWIU_ALLOWED_RATES: set[float] = {17, 15, 14, 12.5, 10, 8.5, 5.5, 3, 2}

    CACHE_TTL_DAYS: int = 90
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_DELAYS: list[int] = [1, 2, 4]

    # --- Computed paths (read-only properties) ---
    @property
    def DATA_DIR(self) -> Path:
        return PROJECT_ROOT / "data" / "classification"

    @property
    def KB_PATH(self) -> Path:
        return self.DATA_DIR / "ryczalt_pkwiu.json"

    @property
    def TEST_CASES_PATH(self) -> Path:
        return self.DATA_DIR / "test_cases.json"

    @property
    def CACHE_DB_PATH(self) -> Path:
        return PROJECT_ROOT / "data" / "cache.db"

    @property
    def RESULTS_DIR(self) -> Path:
        return PROJECT_ROOT / "results"

    # --- Validators ---
    @model_validator(mode="after")
    def validate_encryption_master_key(self) -> "Settings":
        if not self.ENCRYPTION_MASTER_KEY:
            raise ValueError(
                "ENCRYPTION_MASTER_KEY must be set. "
                'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        try:
            Fernet(self.ENCRYPTION_MASTER_KEY.encode())
        except Exception as exc:
            raise ValueError("ENCRYPTION_MASTER_KEY is not a valid Fernet key") from exc
        return self

    @model_validator(mode="after")
    def validate_secret_key_in_prod(self) -> "Settings":
        if self.ENVIRONMENT == "prod" and self.SECRET_KEY == "supersecret_dev_key_replace_in_prod":
            raise ValueError(
                "SECRET_KEY must be changed from the default value in production. "
                "Set a strong random secret via the SECRET_KEY environment variable."
            )
        return self

    @property
    def DATABASE_URL_asyncpg(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
