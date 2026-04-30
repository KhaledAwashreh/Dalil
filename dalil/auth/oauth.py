"""
Base OAuth2 handler for all providers.

Provides common OAuth2 flow: authorize → callback → token exchange.
"""

from __future__ import annotations

import base64
import hashlib
import os
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from dalil.auth.models import OAuthState, ProviderType, Token


class OAuthProvider(ABC):
    """Abstract base class for OAuth providers."""

    provider_type: ProviderType

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Generate the authorization URL for the OAuth flow."""
        pass

    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> Token:
        """Exchange authorization code for access token."""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Token:
        """Refresh an expired access token."""
        pass

    @staticmethod
    def generate_state() -> str:
        """Generate a random state parameter for CSRF protection."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")

    @staticmethod
    def _basic_auth_header(client_id: str, client_secret: str) -> dict:
        """Create Basic Auth header for token endpoint."""
        credentials = f"{client_id}:{client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    @staticmethod
    def hash_code_verifier(verifier: str) -> str:
        """Create S256 code challenge for PKCE."""
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    @staticmethod
    def generate_code_verifier() -> str:
        """Generate a code verifier for PKCE."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
