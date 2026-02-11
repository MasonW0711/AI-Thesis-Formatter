class AppError(Exception):
    """Base application exception."""


class ValidationError(AppError):
    """Raised when user input is invalid."""


class ProcessingError(AppError):
    """Raised when formatting pipeline fails."""
