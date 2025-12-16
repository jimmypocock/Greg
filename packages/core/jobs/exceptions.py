"""
Jobs module exceptions.

Domain-specific exceptions for job operations.
"""


class JobError(Exception):
    """Base exception for job errors."""

    def __init__(self, message: str = "Job error"):
        self.message = message
        super().__init__(self.message)


class JobNotFoundError(JobError):
    """Raised when job is not found."""

    def __init__(self, job_id: str | None = None):
        msg = f"Job {job_id} not found" if job_id else "Job not found"
        super().__init__(msg)


class JobCannotBeCancelledError(JobError):
    """Raised when job cannot be cancelled."""

    def __init__(self, status: str):
        super().__init__(f"Cannot cancel job with status: {status}")


class JobCancellationError(JobError):
    """Raised when job cancellation fails."""

    def __init__(self):
        super().__init__("Failed to cancel job")


class JobAccessDeniedError(JobError):
    """Raised when user tries to access a job they don't own."""

    def __init__(self, job_id: str | None = None):
        msg = f"Access denied to job {job_id}" if job_id else "Access denied to job"
        super().__init__(msg)
