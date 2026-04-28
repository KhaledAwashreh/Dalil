"""
OAuth middleware for protecting API endpoints.

Checks for valid OAuth tokens before allowing access to protected routes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from dalil.auth.models import ProviderType
from dalil.auth.storage import TokenStorage


class OAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to check OAuth authentication for protected paths."""

    def __init__(self, app, token_storage: TokenStorage, protected_paths: list[str] | None = None):
        super().__init__(app)
        self.token_storage = token_storage
        # Paths that require authentication
        self.protected_paths = protected_paths or [
            "/ingest/confluence",
            "/feedback",
        ]

    async def dispatch(self, request: Request, call_next):
        """Check authentication for protected paths."""
        path = request.url.path

        # Check if path is protected
        if any(path.startswith(p) for p in self.protected_paths):
            # Check for OAuth token in Authorization header
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required. Please authenticate via /auth/login/{provider}",
                )

            # Extract token
            token_str = auth_header.replace("Bearer ", "")

            # Verify token exists in storage (simplified check)
            # In production, you'd validate the token properly
            user = None
            for provider in ProviderType:
                stored_token = self.token_storage.get_token(provider)
                if stored_token and stored_token.access_token == token_str:
                    user = stored_token
                    break

            if user is None:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token",
                )

        response = await call_next(request)
        return response


def setup_oauth_middleware(app, token_storage: Optional[TokenStorage]):
    """Add OAuth middleware to the FastAPI app if token storage is available."""
    if token_storage:
        app.add_middleware(OAuthMiddleware, token_storage=token_storage)
