from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def rate_limit_key(request):
    return get_remote_address(request)


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=[settings.rate_limit_default],
    storage_uri=settings.rate_limit_storage_uri,
    headers_enabled=True,
    enabled=settings.rate_limit_enabled,
)