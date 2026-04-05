import os
from pathlib import Path

from dotenv import load_dotenv

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "classification"
KB_PATH = DATA_DIR / "ryczalt_pkwiu.json"
TEST_CASES_PATH = DATA_DIR / "test_cases.json"
CACHE_DB_PATH = PROJECT_ROOT / "data" / "cache.db"
RESULTS_DIR = PROJECT_ROOT / "results"

# Load .env
load_dotenv(PROJECT_ROOT / ".env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Models
FRONT_DESK_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.0

# Confidence threshold — below this → NEEDS_CLARIFICATION
GREEN_CORRIDOR_THRESHOLD = 0.90

# Valid ryczałt rates
VALID_RATES = {2, 3, 5.5, 8.5, 10, 12, 12.5, 14, 15, 17}

# Fatal ambiguities — always reject
FATAL_AMBIGUITIES = {
    "alcohol_threshold_unknown",
}

# Revenue threshold (Art. 12 ust. 1 pkt 4) — JDG business only
# These PKWiU codes have 8.5% up to 100k PLN, 12.5% above
THRESHOLD_PKWIU_PREFIXES = (
    "55",  # 4c: zakwaterowanie (accommodation)
    "72",  # 4e: badania naukowe i prace R&D
    "77.11.10.0",  # 4f: wynajem samochodów osobowych
    "77.12.1",  # 4f: wynajem pozostałych pojazdów
    "77.34.10.0",  # 4f: wynajem statków bez załogi
    "77.35.10.0",  # 4f: wynajem samolotów bez załogi
    "77.39.11.0",  # 4f: wynajem lokomotyw i wagonów
    "77.39.12.0",  # 4f: wynajem kontenerów
    "77.39.13.0",  # 4f: wynajem motocykli i przyczep
    "87",  # 4g: pomoc społeczna z zakwaterowaniem
)
REVENUE_THRESHOLD = 100_000  # PLN per year

# Rates where null PKWiU is allowed
# 14% and 15% added: some wolny zawód and manufacturing cases return null PKWiU
NULL_PKWIU_ALLOWED_RATES = {17, 15, 14, 12.5, 10, 8.5, 5.5, 3, 2}

# Cache
CACHE_TTL_DAYS = 90

# LLM retry
LLM_MAX_RETRIES = 3
LLM_RETRY_DELAYS = [1, 2, 4]  # seconds
