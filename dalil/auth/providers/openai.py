"""
OpenAI OAuth2 provider.
"""

from __future__ import annotations

import httpx
from datetime import datetime, timezone

from dalil.auth.models import ProviderType, Token, User
from dalil.auth.oauth import OAuthProvider


class OpenAIOAuthProvider(OAuthProvider):
    """OpenAI OAuth provider."""

    provider_type = ProviderType("openai")

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.auth_url = "https://platform.openai.com/oauth/authorize"
        self.token_url = "https://api.openai.com/oauth/token"
        self.user_url = "https://api.openai.com/v1/me"
        self.scopes = ["api", "models.read"]

    def get_authorization_url(self, state: str) -> str:
        """Generate OpenAI authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": " ".join(self.scopes),
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.auth_url}?{query}"

    async def exchange_code_for_token(self, code: str) -> Token:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

            expires_at = None
            if "expires_in" in data:
                expires_at = datetime.now(timezone.utc).timestamp() + data["expires_in"]

            return Token(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_type=data.get("token_type", "Bearer"),
                expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc) if expires_at else None,
                scope=data.get("scope"),
                provider=self.provider_type,
            )

    async def refresh_token(self, refresh_token: str) -> Token:
        """Refresh an expired access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

            expires_at = None
            if "expires_in" in data:
                expires_at = datetime.now(timezone.utc).timestamp() + data["expires_in"]

            return Token(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", refresh_token),
                token_type=data.get("token_type", "Bearer"),
                expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc) if expires_at else None,
                scope=data.get("scope"),
                provider=self.provider_type,
            )

    async def get_user_info(self, token: Token) -> User:
        """Retrieve user information from OpenAI API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.user_url,
                headers={"Authorization": f"Bearer {token.access_token}"},
            )
            response.raise_for_status()
            data = response.json()

            return User(
                id=data.get("id", ""),
                email=data.get("email", ""),
                name=data.get("name", ""),
                provider=self.provider_type,
                avatar_url=data.get("avatar_url"),
            )
