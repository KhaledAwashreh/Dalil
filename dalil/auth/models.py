"""
Pydantic models for authentication and OAuth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported OAuth providers."""
    ATLASSIAN = "atlassian"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class OAuthState(BaseModel):
    """OAuth state parameter for CSRF protection."""
    state: str
    provider: ProviderType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    redirect_uri: str = ""


class Token(BaseModel):
    """OAuth token with metadata."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    provider: ProviderType
    user_id: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class User(BaseModel):
    """Authenticated user information."""
    id: str
    email: str
    name: str = ""
    provider: ProviderType
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
