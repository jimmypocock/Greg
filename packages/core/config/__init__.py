"""
Configuration module.

Provides application settings and config validation.
"""

from packages.core.config.settings import Config
from packages.core.config.validation import (
    ConfigurationError,
    validate_config,
    validate_config_or_exit,
)

__all__ = [
    "Config",
    "ConfigurationError",
    "validate_config",
    "validate_config_or_exit",
]
