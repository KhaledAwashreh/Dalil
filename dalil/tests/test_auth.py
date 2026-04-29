"""
Tests for the authentication module.

Covers OAuth models, token storage, and provider implementations.
"""

import pytest
from datetime import datetime, timezone

from dalil.auth.models import Token, User, OAuthState, ProviderType
from dalil.auth.storage import TokenStorage
from dalil.auth.providers.atlassian import AtlassianOAuthProvider


class TestModels:
    """Tests for Pydantic models."""

    def test_provider_type_values(self):
        """ProviderType should have expected values."""
        assert ProviderType.ATLASSIAN == "atlassian"
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.ANTHROPIC == "anthropic"

    def test_token_creation(self):
        """Token should be created with required fields."""
        token = Token(
            access_token="test-access",
            provider=ProviderType.ATLASSIAN,
        )
        assert token.access_token == "test-access"
        assert token.token_type == "Bearer"
        assert token.provider == ProviderType.ATLASSIAN

    def test_user_creation(self):
        """User should be created with required fields."""
        user = User(
            id="123",
            email="test@example.com",
            provider=ProviderType.ATLASSIAN,
        )
        assert user.id == "123"
        assert user.email == "test@example.com"

    def test_oauth_state_creation(self):
        """OAuthState should generate correctly."""
        state = OAuthState(state="abc123", provider=ProviderType.ATLASSIAN)
        assert state.state == "abc123"
        assert isinstance(state.created_at, datetime)


class TestTokenStorage:
    """Tests for encrypted token storage."""

    def test_save_and_get_token(self, tmp_path):
        """Should save and retrieve tokens correctly."""
        storage = TokenStorage(storage_path=str(tmp_path / ".auth"))

        token = Token(
            access_token="test-token",
            refresh_token="refresh-token",
            provider=ProviderType.ATLASSIAN,
            user_id="user123",
        )
        storage.save_token(token)

        retrieved = storage.get_token(ProviderType.ATLASSIAN, "user123")
        assert retrieved is not None
        assert retrieved.access_token == "test-token"
        assert retrieved.refresh_token == "refresh-token"

    def test_delete_token(self, tmp_path):
        """Should delete tokens correctly."""
        storage = TokenStorage(storage_path=str(tmp_path / ".auth"))

        token = Token(
            access_token="test-token",
            provider=ProviderType.ATLASSIAN,
            user_id="user123",
        )
        storage.save_token(token)
        storage.delete_token(ProviderType.ATLASSIAN, "user123")

        retrieved = storage.get_token(ProviderType.ATLASSIAN, "user123")
        assert retrieved is None

    def test_save_and_get_user(self, tmp_path):
        """Should save and retrieve users correctly."""
        storage = TokenStorage(storage_path=str(tmp_path / ".auth"))

        user = User(
            id="user123",
            email="test@example.com",
            name="Test User",
            provider=ProviderType.ATLASSIAN,
        )
        storage.save_user(user)

        retrieved = storage.get_user(ProviderType.ATLASSIAN, "user123")
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
        assert retrieved.name == "Test User"


class TestAtlassianOAuthProvider:
    """Tests for Atlassian OAuth provider."""

    def test_authorization_url_generation(self):
        """Should generate valid authorization URL."""
        provider = AtlassianOAuthProvider(
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
        )
        state = "test-state"
        url = provider.get_authorization_url(state)

        assert "https://auth.atlassian.com/authorize" in url
        assert "client_id=test-client" in url
        assert f"state={state}" in url

    def test_generate_state(self):
        """Should generate unique state parameters."""
        provider = AtlassianOAuthProvider(
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost:8000",
        )
        state1 = provider.generate_state()
        state2 = provider.generate_state()

        assert state1 != state2
        assert len(state1) > 0


class TestAuthDependencies:
    """Tests for FastAPI OAuth dependencies."""

    def test_get_token_storage(self, tmp_path):
        """Should return token storage instance."""
        from dalil.auth.dependencies import get_token_storage
        from dalil.auth.storage import TokenStorage

        # Mock the token_storage in main module
        import dalil.api.main as main_module
        main_module.token_storage = TokenStorage(storage_path=str(tmp_path / ".auth"))

        storage = get_token_storage()
        assert isinstance(storage, TokenStorage)

        # Cleanup
        main_module.token_storage = None


class TestAuthUtils:
    """Tests for OAuth utility functions."""

    def test_get_token_for_provider(self, tmp_path):
        """Should retrieve token for provider."""
        from dalil.auth.storage import TokenStorage
        from dalil.auth.models import Token, ProviderType
        from dalil.auth.utils import get_token_for_provider

        storage = TokenStorage(storage_path=str(tmp_path / ".auth"))
        token = Token(
            access_token="test-token",
            provider=ProviderType.ATLASSIAN,
        )
        storage.save_token(token)

        retrieved = get_token_for_provider(ProviderType.ATLASSIAN, storage)
        assert retrieved is not None
        assert retrieved.access_token == "test-token"

    def test_is_authenticated_true(self, tmp_path):
        """Should return True when authenticated."""
        from dalil.auth.storage import TokenStorage
        from dalil.auth.models import Token, ProviderType
        from dalil.auth.utils import is_authenticated

        storage = TokenStorage(storage_path=str(tmp_path / ".auth"))
        token = Token(
            access_token="test-token",
            provider=ProviderType.ATLASSIAN,
        )
        storage.save_token(token)

        assert is_authenticated(ProviderType.ATLASSIAN, storage) is True

    def test_is_authenticated_false(self, tmp_path):
        """Should return False when not authenticated."""
        from dalil.auth.storage import TokenStorage
        from dalil.auth.models import ProviderType
        from dalil.auth.utils import is_authenticated

        storage = TokenStorage(storage_path=str(tmp_path / ".auth"))

        assert is_authenticated(ProviderType.ATLASSIAN, storage) is False

    def test_get_authorization_header(self):
        """Should create correct Authorization header."""
        from dalil.auth.models import Token, ProviderType
        from dalil.auth.utils import get_authorization_header

        token = Token(
            access_token="my-token",
            token_type="Bearer",
            provider=ProviderType.ATLASSIAN,
        )

        header = get_authorization_header(token)
        assert header == {"Authorization": "Bearer my-token"}

