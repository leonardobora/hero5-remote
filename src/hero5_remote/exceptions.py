"""Exceptions raised by hero5-remote."""


class GoProError(Exception):
    """Base exception for all hero5-remote errors."""


class GoProConnectionError(GoProError):
    """Raised when the camera cannot be reached over Wi-Fi."""


class GoProTimeoutError(GoProConnectionError):
    """Raised when a request to the camera times out."""


class GoProResponseError(GoProError):
    """Raised when the camera returns a non-2xx or unparseable response."""
