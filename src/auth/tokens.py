"""
Token utilities.

Provides token generation and hashing for:
- API keys (greg_xxx format)
- Invite codes (8-character alphanumeric)

JWT tokens are handled by FastAPI-Users.
"""

import hashlib
import secrets


# Public functions

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix).
        - full_key: The complete API key to return to the user (only shown once).
        - key_hash: Hash to store in the database.
        - key_prefix: First 12 chars for identification.
    """
    key = f"greg_{secrets.token_urlsafe(32)}"
    key_hash = hash_token(key)
    key_prefix = key[:12]

    return key, key_hash, key_prefix


def generate_invite_code() -> str:
    """
    Generate a unique invite code.

    Returns:
        8-character alphanumeric code.
    """
    return secrets.token_urlsafe(6)[:8]


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.

    Args:
        token: Plain token string.

    Returns:
        SHA-256 hash of the token.
    """
    return hashlib.sha256(token.encode()).hexdigest()


__all__ = [
    "generate_api_key",
    "generate_invite_code",
    "hash_token",
]
