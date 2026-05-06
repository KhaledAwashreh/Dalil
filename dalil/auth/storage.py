"""
Encrypted token storage for OAuth tokens.

Uses Fernet symmetric encryption from the cryptography package.
Tokens are encrypted before storage and decrypted on retrieval.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

from dalil.auth.models import Token, User, ProviderType


class TokenStorage:
    """Encrypted storage for OAuth tokens and user data."""

    def __init__(self, storage_path: str = ".dalil_auth", encryption_key: Optional[bytes] = None):
        """
        Initialize token storage.

        Args:
            storage_path: Directory to store encrypted tokens
            encryption_key: Fernet key (generates one if not provided)
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        if encryption_key is None:
            key_file = self.storage_path / ".key"
            if key_file.exists():
                encryption_key = key_file.read_bytes()
            else:
                encryption_key = Fernet.generate_key()
                key_file.write_bytes(encryption_key)

        self.cipher = Fernet(encryption_key)
        self.tokens_file = self.storage_path / "tokens.enc"
        self.users_file = self.storage_path / "users.enc"

    def _encrypt(self, data: str) -> bytes:
        """Encrypt data."""
        return self.cipher.encrypt(data.encode())

    def _decrypt(self, data: bytes) -> str:
        """Decrypt data."""
        return self.cipher.decrypt(data).decode()

    def save_token(self, token: Token) -> None:
        """Save or update an OAuth token."""
        tokens = self._load_all_tokens()
        key = f"{token.provider.value}:{token.user_id or 'default'}"
        tokens[key] = token.model_dump(mode='json')
        self._save_all_tokens(tokens)

    def get_token(self, provider: ProviderType, user_id: str = "default") -> Optional[Token]:
        """Retrieve a token for a provider and user."""
        tokens = self._load_all_tokens()
        key = f"{provider.value}:{user_id}"
        if key not in tokens:
            return None
        return Token(**tokens[key])

    def delete_token(self, provider: ProviderType, user_id: str = "default") -> None:
        """Delete a token."""
        tokens = self._load_all_tokens()
        key = f"{provider.value}:{user_id}"
        if key in tokens:
            del tokens[key]
            self._save_all_tokens(tokens)

    def save_user(self, user: User) -> None:
        """Save or update user information."""
        users = self._load_all_users()
        key = f"{user.provider.value}:{user.id}"
        users[key] = user.model_dump(mode='json')
        self._save_all_users(users)

    def get_user(self, provider: ProviderType, user_id: str = "default") -> Optional[User]:
        """Retrieve user information."""
        users = self._load_all_users()
        key = f"{provider.value}:{user_id}"
        if key not in users:
            return None
        return User(**users[key])

    def _load_all_tokens(self) -> dict:
        """Load all tokens from encrypted storage."""
        if not self.tokens_file.exists():
            return {}
        try:
            encrypted_data = self.tokens_file.read_bytes()
            decrypted = self._decrypt(encrypted_data)
            return json.loads(decrypted)
        except Exception:
            return {}

    def _save_all_tokens(self, tokens: dict) -> None:
        """Save all tokens to encrypted storage."""
        json_data = json.dumps(tokens)
        encrypted = self._encrypt(json_data)
        self.tokens_file.write_bytes(encrypted)

    def _load_all_users(self) -> dict:
        """Load all users from encrypted storage."""
        if not self.users_file.exists():
            return {}
        try:
            encrypted_data = self.users_file.read_bytes()
            decrypted = self._decrypt(encrypted_data)
            return json.loads(decrypted)
        except Exception:
            return {}

    def _save_all_users(self, users: dict) -> None:
        """Save all users to encrypted storage."""
        json_data = json.dumps(users)
        encrypted = self._encrypt(json_data)
        self.users_file.write_bytes(encrypted)
