"""Live preview streaming bridge for the GoPro Hero 5 Black.

The Hero 5 exposes a UDP H.264 preview stream on udp://10.5.5.9:8554 after
sending a start command. This module turns that stream into a Windows virtual
camera that OBS, Zoom, Teams and Discord can consume.

Dependencies for streaming are optional:

    pip install hero5-remote[stream]

On Windows you also need a virtual-camera driver installed. The easiest path
is to install OBS Studio, which registers the OBS Virtual Camera driver that
``pyvirtualcam`` reuses.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import threading
import time
from typing import TYPE_CHECKING, Callable

from .client import DEFAULT_HOST
from .commands import GoPro
from .exceptions import GoProError

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_UDP_URL = f"udp://{DEFAULT_HOST}:8554"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 30


class StreamingError(GoProError):
    """Raised when the streaming pipeline cannot be started."""


def _import_optional(name: str, install_hint: str):
    try:
        return __import__(name)
    except ImportError as exc:
        raise StreamingError(
            f"{name} is required for streaming. {install_hint}"
        ) from exc


class StreamController:
    """Start/stop the GoPro preview stream and bridge it to a virtual camera."""

    def __init__(self, gopro: GoPro | None = None) -> None:
        self.gopro = gopro or GoPro()
        self._ffmpeg: subprocess.Popen | None = None
        self._stop_event = threading.Event()

    def start_camera_stream(self) -> None:
        """Tell the GoPro to start the UDP preview stream.

        Endpoint validated against KonradIT/goprowifihack HERO4/Livestreaming.md
        and linked from HERO5/README.md.
        """
        self.gopro.client.get(
            "/execute",
            params={"p1": "gpStream", "a1": "proto_v2", "c1": "restart"},
        )
        logger.info("GoPro preview stream started")

    def stop_camera_stream(self) -> None:
        """Stop the GoPro preview stream.

        The public docs do not expose a dedicated 'stop stream' command. The
        stream is stopped implicitly by changing the camera mode or powering
        off. We send a mode change to video+normal sub-mode, which reliably
        ends the preview on Hero 5 Black.
        """
        from .commands import Mode, SubMode

        self.gopro.set_mode(Mode.VIDEO)
        self.gopro.set_sub_mode(Mode.VIDEO, SubMode.VIDEO)
        logger.info("GoPro preview stream stopped (mode changed to video)")

    def set_bitrate(self, bps: int) -> None:
        """Set the stream bitrate in bits per second (setting 62)."""
        self.gopro.set_setting(62, bps)
        logger.info("Stream bitrate set to %d bps", bps)

    def set_window_size(self, size_id: int) -> None:
        """Set the stream window size (setting 64)."""
        self.gopro.set_setting(64, size_id)
        logger.info("Stream window size set to %d", size_id)

    def _build_ffmpeg_command(
        self,
        width: int,
        height: int,
        fps: int,
        udp_url: str,
    ) -> list[str]:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise StreamingError(
                "ffmpeg not found in PATH. Install ffmpeg and add it to PATH."
            )

        return [
            ffmpeg,
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-i",
            udp_url,
            "-vf",
            f"scale={width}:{height},format=pix_fmts=rgb24",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "pipe:1",
        ]

    def serve_virtual_camera(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        fps: int = DEFAULT_FPS,
        udp_url: str = DEFAULT_UDP_URL,
        on_frame: Callable | None = None,
    ) -> None:
        """Bridge the UDP stream to a Windows virtual camera via pyvirtualcam.

        This blocks until stop() is called or the stream ends.
        """
        pyvirtualcam = _import_optional(
            "pyvirtualcam",
            "Install with: pip install hero5-remote[stream]",
        )
        np = _import_optional(
            "numpy",
            "Install with: pip install hero5-remote[stream]",
        )

        if shutil.which("ffmpeg") is None:
            raise StreamingError(
                "ffmpeg is required. Download it from https://ffmpeg.org/download.html"
            )

        frame_size = width * height * 3
        command = self._build_ffmpeg_command(width, height, fps, udp_url)

        self._stop_event.clear()
        self._ffmpeg = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=frame_size * 2,
        )

        # Log ffmpeg errors on a side thread.
        def _log_stderr() -> None:
            if self._ffmpeg is None or self._ffmpeg.stderr is None:
                return
            for line in iter(self._ffmpeg.stderr.readline, b""):
                if not line:
                    break
                logger.debug("ffmpeg: %s", line.decode("utf-8", errors="replace").rstrip())

        threading.Thread(target=_log_stderr, daemon=True).start()

        fmt = getattr(pyvirtualcam.PixelFormat, "RGB", None)
        if fmt is None:
            fmt = pyvirtualcam.PixelFormat.RGB

        with pyvirtualcam.Camera(width=width, height=height, fps=fps, fmt=fmt) as cam:
            logger.info("Virtual camera active: %s", cam.device)
            while not self._stop_event.is_set():
                if self._ffmpeg is None or self._ffmpeg.poll() is not None:
                    raise StreamingError("ffmpeg process ended unexpectedly")

                raw = self._ffmpeg.stdout.read(frame_size)
                if len(raw) < frame_size:
                    time.sleep(0.001)
                    continue

                frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
                cam.send(frame)
                cam.sleep_until_next_frame()
                if on_frame:
                    on_frame(frame)

    def stop(self) -> None:
        """Signal the streaming loop and ffmpeg to stop."""
        self._stop_event.set()
        if self._ffmpeg is not None and self._ffmpeg.poll() is None:
            self._ffmpeg.terminate()
            try:
                self._ffmpeg.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._ffmpeg.kill()
        self._ffmpeg = None
