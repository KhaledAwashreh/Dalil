"""
Utility functions for OAuth authentication.
"""

from __future__ import annotations

from typing import Optional

from dalil.auth.models import Token, ProviderType
from dalil.auth.storage import TokenStorage


def get_token_for_provider(
    provider: ProviderType,
    token_storage: TokenStorage,
    user_id: str = "default",
) -> Optional[Token]:
    """Get a valid token for the specified provider.

    Returns None if not authenticated.
    """
    return token_storage.get_token(provider, user_id)


def is_authenticated(
    provider: ProviderType,
    token_storage: TokenStorage,
    user_id: str = "default",
) -> bool:
    """Check if user is authenticated with the provider."""
    token = token_storage.get_token(provider, user_id)
    return token is not None


def get_authorization_header(token: Token) -> dict[str, str]:
    """Create Authorization header from token."""
    return {"Authorization": f"{token.token_type} {token.access_token}"}


def token_expired(token: Token) -> bool:
    """Check if token is expired."""
    if token.expires_at is None:
        return False
    from datetime import datetime, timezone
    return datetime.now(timezone.utc) >= token.expires_at
