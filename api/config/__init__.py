"""
Configuration module.

Provides application settings and config validation.
"""

from api.config.settings import Config
from api.config.validation import (
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
