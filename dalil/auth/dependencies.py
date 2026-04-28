"""
FastAPI dependencies for OAuth token injection.

Provides dependency functions to get OAuth tokens for API endpoints.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query

from dalil.auth.models import ProviderType, Token
from dalil.auth.storage import TokenStorage


def get_token_storage() -> TokenStorage:
    """Get the token storage instance from app state.

    This should be overridden with the actual storage instance in main.py.
    """
    from dalil.api.main import token_storage
    if token_storage is None:
        raise HTTPException(status_code=500, detail="OAuth not configured")
    return token_storage


async def get_oauth_token(
    provider: ProviderType,
    token_storage: TokenStorage = Depends(get_token_storage),
) -> Token:
    """Get a valid OAuth token for the specified provider.

    Raises 401 if not authenticated.
    """
    token = token_storage.get_token(provider)
    if token is None:
        raise HTTPException(
            status_code=401,
            detail=f"Not authenticated with {provider.value}. Call /auth/login/{provider.value} first.",
        )
    return token


async def get_atlassian_token(
    token: Token = Depends(lambda: get_oauth_token(ProviderType.ATLASSIAN)),
) -> Token:
    """Get Atlassian OAuth token."""
    return token


async def get_openai_token(
    token: Token = Depends(lambda: get_oauth_token(ProviderType.OPENAI)),
) -> Token:
    """Get OpenAI OAuth token."""
    return token


async def get_anthropic_token(
    token: Token = Depends(lambda: get_oauth_token(ProviderType.ANTHROPIC)),
) -> Token:
    """Get Anthropic OAuth token."""
    return token


async def get_optional_oauth_token(
    provider: ProviderType,
    token_storage: TokenStorage = Depends(get_token_storage),
) -> Optional[Token]:
    """Get OAuth token if available, otherwise return None."""
    return token_storage.get_token(provider)
