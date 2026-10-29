"""
Shared slowapi rate-limiter instance.

Key function: uses the bearer token as the bucket key so each authenticated
user has their own counter. Unauthenticated requests fall back to IP address.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _auth_or_ip(request: Request) -> str:
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:]            # token is user-unique → per-user bucket
    return get_remote_address(request)


limiter = Limiter(key_func=_auth_or_ip)
