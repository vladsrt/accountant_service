import os

from cryptography.fernet import Fernet

os.environ.setdefault("ENCRYPTION_MASTER_KEY", Fernet.generate_key().decode())
os.environ.setdefault("KSEF_BASE_URL", "https://api-test.ksef.mf.gov.pl")
