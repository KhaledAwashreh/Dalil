"""
Authentication module for Dalil.

Provides OAuth2/OpenID Connect integration with Atlassian, OpenAI, and Anthropic.
"""

from dalil.auth.models import User, Token, ProviderType, OAuthState
from dalil.auth.storage import TokenStorage
from dalil.auth.utils import get_token_for_provider, is_authenticated

__all__ = [
    "User", "Token", "ProviderType", "OAuthState",
    "TokenStorage", "get_token_for_provider", "is_authenticated",
]
