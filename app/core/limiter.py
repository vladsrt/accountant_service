from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Shared rate limiter
if settings.ENVIRONMENT == "test":
    limiter = Limiter(key_func=get_remote_address)
else:
    limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
