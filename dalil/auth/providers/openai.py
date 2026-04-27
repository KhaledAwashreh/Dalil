"""
OpenAI OAuth2 provider (stub).

Note: OpenAI primarily uses API keys. OAuth SSO is limited.
This is a placeholder for future implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from dalil.auth.models import ProviderType, Token, User
from dalil.auth.oauth import OAuthProvider


class OpenAIOAuthProvider(OAuthProvider):
    """OpenAI OAuth provider (placeholder).

    OpenAI's platform currently relies on API keys rather than OAuth.
    This stub is prepared for potential future OAuth support.
    """

    provider_type = ProviderType.OPEN_AI

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        # OpenAI OAuth endpoints (when available)
        self.auth_url = "https://platform.openai.com/oauth/authorize"
        self.token_url = "https://platform.openai.com/oauth/token"

    def get_authorization_url(self, state: str) -> str:
        """Generate OpenAI authorization URL (placeholder)."""
        # TODO: Implement when OpenAI releases OAuth support
        raise NotImplementedError("OpenAI OAuth not yet supported")

    async def exchange_code_for_token(self, code: str) -> Token:
        """Exchange code for token (placeholder)."""
        raise NotImplementedError("OpenAI OAuth not yet supported")

    async def refresh_token(self, refresh_token: str) -> Token:
        """Refresh token (placeholder)."""
        raise NotImplementedError("OpenAI OAuth not yet supported")

    async def get_user_info(self, token: Token) -> User:
        """Get user info (placeholder)."""
        raise NotImplementedError("OpenAI OAuth not yet supported")
