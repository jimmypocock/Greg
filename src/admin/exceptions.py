"""
Admin module exceptions.

Domain-specific exceptions for admin operations.
"""


class AdminError(Exception):
    """Base exception for admin errors."""

    def __init__(self, message: str = "Admin error"):
        self.message = message
        super().__init__(self.message)


class UserNotFoundError(AdminError):
    """Raised when user is not found."""

    def __init__(self, user_id: str | None = None):
        msg = f"User {user_id} not found" if user_id else "User not found"
        super().__init__(msg)


class InviteNotFoundError(AdminError):
    """Raised when invite is not found."""

    def __init__(self, code: str | None = None):
        msg = f"Invite {code} not found" if code else "Invite not found"
        super().__init__(msg)


class CannotDeleteSelfError(AdminError):
    """Raised when admin tries to delete themselves."""

    def __init__(self):
        super().__init__("Cannot delete yourself")


class CannotDemoteSelfError(AdminError):
    """Raised when admin tries to demote themselves."""

    def __init__(self):
        super().__init__("Cannot demote yourself")


class CannotDisableSelfError(AdminError):
    """Raised when admin tries to disable themselves."""

    def __init__(self):
        super().__init__("Cannot disable yourself")


class InviteAlreadyUsedError(AdminError):
    """Raised when trying to revoke a used invite."""

    def __init__(self):
        super().__init__("Cannot revoke used invite")


class InvalidRoleError(AdminError):
    """Raised when role is invalid."""

    def __init__(self, role: str):
        super().__init__(f"Invalid role: {role}")


class InviteGenerationError(AdminError):
    """Raised when invite code generation fails."""

    def __init__(self):
        super().__init__("Failed to generate unique invite code")
