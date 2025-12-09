"""
Configuration validation.

Validates required environment variables on startup.
"""

import os
import sys


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""

    pass


# Required environment variables (no defaults allowed)
REQUIRED_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET_KEY",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "UPLOAD_DIR",
    "VECTOR_STORE_DIR",
]

# Optional vars that will use None if not set (auto-detection or optional features)
OPTIONAL_VARS = [
    "EMBEDDING_PROVIDER",  # Auto-detects based on API keys
    "EMBEDDING_MODEL",  # Uses provider default
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "ALLOWED_ORIGINS",
    "CORS_ALLOW_ALL",
]


def validate_config() -> None:
    """
    Validate that all required environment variables are set.

    Raises:
        ConfigurationError: If any required variable is missing.
    """
    missing = []

    for var in REQUIRED_VARS:
        value = os.environ.get(var, "").strip()
        if not value:
            missing.append(var)

    if missing:
        missing_list = "\n  - ".join(missing)
        raise ConfigurationError(
            f"Missing required environment variables:\n  - {missing_list}\n\n"
            f"Please set these in your .env file. See .env.example for reference."
        )


def validate_config_or_exit() -> None:
    """
    Validate config and exit with error message if invalid.

    Use this at application startup.
    """
    try:
        validate_config()
    except ConfigurationError as e:
        print(f"\nConfiguration Error:\n{e}", file=sys.stderr)
        sys.exit(1)


def get_required(var: str) -> str:
    """
    Get a required environment variable.

    Args:
        var: Variable name

    Returns:
        Variable value

    Raises:
        ConfigurationError: If variable is not set
    """
    value = os.environ.get(var, "").strip()
    if not value:
        raise ConfigurationError(f"Required environment variable not set: {var}")
    return value


def get_optional(var: str, default: str | None = None) -> str | None:
    """
    Get an optional environment variable.

    Args:
        var: Variable name
        default: Default value if not set

    Returns:
        Variable value or default
    """
    value = os.environ.get(var, "").strip()
    return value if value else default
