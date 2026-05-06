"""
FastAPI routes for OAuth authentication.

Provides login, callback, logout, and token endpoints.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from dalil.auth.models import OAuthState, ProviderType, Token, User
from dalil.auth.storage import TokenStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# In-memory state store (use Redis in production)
_state_store: dict[str, OAuthState] = {}


def setup_oauth_routes(storage: TokenStorage, providers: dict[ProviderType, any]) -> APIRouter:
    """Configure OAuth routes with dependencies."""

    @router.get("/login/{provider}")
    async def login(provider: ProviderType, request: Request):
        """Initiate OAuth login flow."""
        if provider not in providers:
            raise HTTPException(400, f"Unsupported provider: {provider}")

        provider_handler = providers[provider]
        state_str = provider_handler.generate_state()

        # Store state for validation
        redirect_uri = str(request.url_for(f"callback", provider=provider.value))
        _state_store[state_str] = OAuthState(
            state=state_str,
            provider=provider,
            redirect_uri=redirect_uri,
        )

        auth_url = provider_handler.get_authorization_url(state_str)
        return RedirectResponse(url=auth_url)

    @router.get("/callback/{provider}")
    async def callback(
        provider: ProviderType,
        code: str = Query(...),
        state: str = Query(...),
    ):
        """Handle OAuth callback."""
        if state not in _state_store:
            raise HTTPException(400, "Invalid state parameter")

        stored_state = _state_store.pop(state)
        if stored_state.provider != provider:
            raise HTTPException(400, "Provider mismatch")

        if provider not in providers:
            raise HTTPException(400, f"Unsupported provider: {provider}")

        provider_handler = providers[provider]

        # Exchange code for token
        token = await provider_handler.exchange_code_for_token(code)

        # Get user info (optional — may fail if read:me scope not granted)
        try:
            user = await provider_handler.get_user_info(token)
        except Exception:
            user = User(id="default", email="", name="unknown", provider=provider)

        # Store token and user
        storage.save_token(token)
        storage.save_user(user)

        return {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
            "user": user.model_dump(mode='json'),
        }

    @router.get("/status")
    async def auth_status(provider: Optional[ProviderType] = Query(None)):
        """Check authentication status."""
        if provider:
            token = storage.get_token(provider)
            user = storage.get_user(provider, token.user_id if token else "default")
            return {
                "authenticated": token is not None,
                "provider": provider.value,
                "user": user.model_dump(mode='json') if user else None,
            }

        # Check all providers
        status = {}
        for p in ProviderType:
            token = storage.get_token(p)
            status[p.value] = token is not None
        return status

    @router.post("/logout")
    async def logout(provider: Optional[ProviderType] = Query(None)):
        """Logout and clear stored tokens."""
        if provider:
            storage.delete_token(provider)
            return {"message": f"Logged out from {provider.value}"}

        # Clear all tokens
        for p in ProviderType:
            storage.delete_token(p)
        return {"message": "Logged out from all providers"}

    @router.get("/tokens/{provider}")
    async def get_token(provider: ProviderType):
        """Retrieve stored token for a provider (for API calls)."""
        token = storage.get_token(provider)
        if not token:
            raise HTTPException(401, f"Not authenticated with {provider.value}")
        return token.model_dump(mode='json')

    return router
