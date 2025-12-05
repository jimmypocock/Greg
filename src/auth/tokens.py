"""
Token utilities.

Provides API key generation and invite code generation.
JWT tokens are handled by FastAPI-Users.
"""

import hashlib
import secrets


def hash_token(token: str) -> str:
    """
    Hash a token for storage.

    Args:
        token: Plain token string.

    Returns:
        SHA-256 hash of the token.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix).
        - full_key: The complete API key to return to the user (only shown once).
        - key_hash: Hash to store in the database.
        - key_prefix: First 12 chars for identification.
    """
    # Generate a secure random key with a prefix for identification
    key = f"greg_{secrets.token_urlsafe(32)}"
    key_hash = hash_token(key)
    key_prefix = key[:12]  # "greg_" + first 7 chars of random part

    return key, key_hash, key_prefix


def generate_invite_code() -> str:
    """
    Generate a unique invite code.

    Returns:
        8-character alphanumeric code.
    """
    return secrets.token_urlsafe(6)[:8]  # 8 chars, URL-safe
