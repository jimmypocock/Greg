"""Collaborator role enum for song sharing permissions."""

from enum import Enum


class CollaboratorRole(str, Enum):
    """Roles for song collaborators."""

    OWNER = "owner"  # Full control: edit, delete, manage collaborators
    EDITOR = "editor"  # Can edit song content
    VIEWER = "viewer"  # Read-only access
