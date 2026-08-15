"""Low-level HTTP client for the GoPro Hero 5 Black Wi-Fi API."""

import json
import logging
import socket
import time
from typing import Any

import requests

from .exceptions import GoProConnectionError, GoProResponseError, GoProTimeoutError

DEFAULT_HOST = "10.5.5.9"
DEFAULT_TIMEOUT = 5
DEFAULT_RETRIES = 3


class GoProClient:
    """HTTP client with retries, timeouts and detailed logging.

    All endpoints are documented in KonradIT/goprowifihack for the HERO5.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.host = host
        self.timeout = timeout
        self.retries = max(1, retries)
        self.control_url = f"http://{host}/gp/gpControl"
        self.media_url = f"http://{host}:8080"
        self._session = requests.Session()
        self._logger = logging.getLogger(self.__class__.__name__)

    def _url(self, path: str, media: bool = False) -> str:
        """Build a URL for control or media endpoints.

        Note: gpMediaList lives on port 8080, while gpMediaMetadata and
        storage commands live on the default HTTP port (80).
        """
        base = self.media_url if media else self.control_url
        return f"{base}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        media: bool = False,
        **kwargs: Any,
    ) -> requests.Response:
        """Send an HTTP request with retry/backoff.

        Raises:
            GoProTimeoutError: if every attempt times out.
            GoProConnectionError: if every attempt fails to connect.
            GoProResponseError: if the camera returns HTTP >= 400.
        """
        url = self._url(path, media=media)
        kwargs.setdefault("timeout", self.timeout)
        last_error: Exception | None = None

        for attempt in range(1, self.retries + 1):
            try:
                self._logger.debug("%s %s (attempt %d)", method, url, attempt)
                response = self._session.request(method, url, **kwargs)
                self._logger.debug(
                    "response %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                response.raise_for_status()
                return response
            except requests.Timeout as exc:
                last_error = GoProTimeoutError(
                    f"Timeout after {self.timeout}s on {method} {url}"
                )
                last_error.__cause__ = exc
                self._logger.warning("attempt %d timed out for %s", attempt, url)
            except requests.ConnectionError as exc:
                last_error = GoProConnectionError(
                    f"Connection error on {method} {url}: {exc}"
                )
                last_error.__cause__ = exc
                self._logger.warning(
                    "attempt %d connection error for %s", attempt, url
                )
            except requests.HTTPError as exc:
                err = GoProResponseError(
                    f"HTTP {exc.response.status_code} from camera: "
                    f"{exc.response.text[:200]}"
                )
                err.__cause__ = exc
                raise err

            if attempt < self.retries:
                backoff = 0.5 * attempt
                self._logger.debug("retrying in %.1fs", backoff)
                time.sleep(backoff)

        assert last_error is not None
        raise last_error

    def get(
        self, path: str, *, media: bool = False, **kwargs: Any
    ) -> requests.Response:
        return self.request("GET", path, media=media, **kwargs)

    def post(
        self, path: str, *, media: bool = False, **kwargs: Any
    ) -> requests.Response:
        return self.request("POST", path, media=media, **kwargs)

    def status(self) -> dict[str, Any]:
        """Fetch the full camera status JSON."""
        response = self.get("/status")
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise GoProResponseError(
                f"Camera returned invalid JSON for status: {response.text[:200]}"
            ) from exc

    def wake_on_lan(
        self,
        mac: str,
        *,
        broadcast: str = "10.5.5.255",
        port: int = 9,
    ) -> None:
        """Send a Wake-on-LAN magic packet to power on the camera.

        The GoPro docs specify IP 10.5.5.9, subnet 255.255.255.0 and port 9.
        WoL requires the camera MAC address obtained during pairing.

        Args:
            mac: Camera MAC address, e.g. ``aa:bb:cc:dd:ee:ff``.
            broadcast: Broadcast address of the GoPro Wi-Fi network.
            port: UDP port for WoL (GoPro docs specify 9).
        """
        clean = mac.replace(":", "").replace("-", "").lower()
        if len(clean) != 12 or not all(c in "0123456789abcdef" for c in clean):
            raise ValueError(f"Invalid MAC address: {mac}")

        magic = bytes.fromhex("FF" * 6 + clean * 16)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic, (broadcast, port))
            self._logger.info(
                "Wake-on-LAN sent to %s via broadcast %s:%d",
                mac,
                broadcast,
                port,
            )
