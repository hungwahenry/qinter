"""
qinter/utils/exceptions.py
"""


class QinterError(Exception):
    """Base exception for Qinter-specific errors."""
    pass


class ExplanationError(QinterError):
    """Raised when error explanation generation fails."""
    pass


class PackageError(QinterError):
    """Raised when package management operations fail."""
    pass


class ConfigurationError(QinterError):
    """Raised when configuration is invalid."""
    pass