"""hero5-remote: Python interface for GoPro Hero 5 Black Wi-Fi API."""

from .client import GoProClient
from .commands import GoPro, Mode, SubMode
from .exceptions import (
    GoProConnectionError,
    GoProError,
    GoProResponseError,
    GoProTimeoutError,
)
from .media import Media
from .streaming import StreamController, StreamingError

__all__ = [
    "GoPro",
    "GoProClient",
    "Media",
    "Mode",
    "SubMode",
    "StreamController",
    "StreamingError",
    "GoProError",
    "GoProConnectionError",
    "GoProTimeoutError",
    "GoProResponseError",
]

__version__ = "0.1.0"
