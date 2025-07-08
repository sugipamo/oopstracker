"""
Exception classes for OOPStracker.
"""


class OOPSTrackerError(Exception):
    """Base exception for all OOPStracker errors."""
    pass


class DatabaseError(OOPSTrackerError):
    """Exception raised for database-related errors."""
    pass


class ValidationError(OOPSTrackerError):
    """Exception raised for validation errors."""
    pass


class CodeAnalysisError(OOPSTrackerError):
    """Exception raised for code analysis errors."""
    pass


class ConfigurationError(OOPSTrackerError):
    """Exception raised for configuration errors."""
    pass