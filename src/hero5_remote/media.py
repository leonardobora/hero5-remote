"""Media browsing and management for the GoPro Hero 5 Black."""

from typing import Any, Optional

from .client import GoProClient
from .exceptions import GoProError


class Media:
    """List, inspect and delete files stored on the camera SD card."""

    def __init__(self, client: GoProClient) -> None:
        self.client = client

    def list(self) -> dict[str, Any]:
        """Return the JSON media list from the SD card.

        Endpoint: ``GET http://10.5.5.9:8080/gp/gpMediaList``
        """
        return self.client.get("/gp/gpMediaList", media=True).json()

    def video_info(self, path: str) -> dict[str, Any]:
        """Return video metadata (duration, tags).

        Endpoint: ``GET /gp/gpMediaMetadata?p=<path>&t=videoinfo``
        """
        return self.client.get(
            "/gp/gpMediaMetadata",
            params={"p": path, "t": "videoinfo"},
        ).json()

    def detailed_info(self, path: str) -> dict[str, Any]:
        """Return detailed v4 metadata for a video or photo.

        Endpoint: ``GET /gp/gpMediaMetadata?p=<path>&t=v4info``
        """
        return self.client.get(
            "/gp/gpMediaMetadata",
            params={"p": path, "t": "v4info"},
        ).json()

    def exif(self, path: str) -> dict[str, Any]:
        """Return EXIF metadata for a JPG photo."""
        return self.client.get(
            "/gp/gpMediaMetadata",
            params={"p": path, "t": "exif"},
        ).json()

    def thumbnail(self, path: str) -> bytes:
        """Return raw thumbnail bytes for a video or photo."""
        return self.client.get(
            "/gp/gpMediaMetadata",
            params={"p": path},
        ).content

    def delete(self, path: str) -> None:
        """Delete a single file.

        Args:
            path: File path as returned by the media list, e.g.
                ``/100GOPRO/GOPR0001.JPG``.
        """
        self.client.get(
            "/command/storage/delete",
            params={"p": path},
        )

    def delete_last(self) -> None:
        """Delete the most recently captured media file."""
        self.client.get("/command/storage/delete/last")

    def delete_all(self) -> None:
        """Reformat the SD card, deleting ALL media. Use with caution."""
        self.client.get("/command/storage/delete/all")
