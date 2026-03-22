"""Shared rate limiter for all API routes."""
from fastapi import Request
from slowapi import Limiter

limiter = Limiter(key_func=lambda request: request.client.host if request.client else "unknown")
