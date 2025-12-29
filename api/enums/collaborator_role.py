"""Collaborator role enum for song sharing permissions."""

from enum import Enum


class CollaboratorRole(str, Enum):
    """Roles for song collaborators."""

    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"
