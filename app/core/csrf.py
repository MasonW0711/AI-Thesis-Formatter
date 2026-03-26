"""CSRF protection for API endpoints.

Uses the double-submit cookie pattern:
1. Client fetches /api/csrf-token → receives token in response body
2. Client includes token in X-CSRF-Token header on mutating requests
3. Server validates token matches before processing

This avoids server-side session storage and works for both browser/API clients.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# In-memory token store: token → (created_at, client_ip)
# Tokens valid for 1 hour; cleaned up on access.
_token_store: dict[str, tuple[float, str]] = {}
_TOKEN_TTL_SEC = 3600


def _clean_expired() -> None:
    now = time.time()
    for k, (created, _) in list(_token_store.items()):
        if now - created > _TOKEN_TTL_SEC:
            del _token_store[k]


def generate_csrf_token(client_ip: str) -> str:
    """Generate a CSRF token for the given client IP."""
    _clean_expired()
    token = secrets.token_urlsafe(32)
    _token_store[token] = (time.time(), client_ip)
    return token


def validate_csrf_token(token: str | None, client_ip: str) -> bool:
    """Validate a CSRF token. Returns True if valid, False otherwise."""
    if not token:
        return False
    _clean_expired()
    record = _token_store.get(token)
    if not record:
        return False
    created_at, ip = record
    if time.time() - created_at > _TOKEN_TTL_SEC:
        del _token_store[token]
        return False
    # Optional: strict IP match (comment out if clients behind same proxy)
    # if ip != client_ip:
    #     return False
    del _token_store[token]  # Single-use
    return True


@dataclass
class CSRFState:
    """CSRF state returned to client after token fetch."""
    csrf_token: str


class CSRFDependency:
    """FastAPI dependency for CSRF validation on mutating endpoints."""

    def __init__(self, methods: list[str] | None = None):
        """
        Args:
            methods: HTTP methods to protect. Defaults to non-GET safe methods.
        """
        self.methods = methods or ["POST", "PUT", "PATCH", "DELETE"]

    async def __call__(self, request: Request) -> None:
        if request.method in self.methods:
            token = request.headers.get("x-csrf-token")
            client_ip = request.client.host if request.client else "unknown"
            if not validate_csrf_token(token, client_ip):
                raise HTTPException(
                    status_code=403,
                    detail="CSRF token 無效或已過期，請先呼叫 /api/csrf-token取得新權杖。",
                )
