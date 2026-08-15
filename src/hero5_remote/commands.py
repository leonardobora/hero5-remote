"""High-level control operations for the GoPro Hero 5 Black."""

from dataclasses import dataclass
from typing import Any, Optional

from .client import DEFAULT_HOST, DEFAULT_RETRIES, DEFAULT_TIMEOUT, GoProClient
from .exceptions import GoProError


class Mode:
    """Primary capture modes."""

    VIDEO = 0
    PHOTO = 1
    MULTISHOT = 2


class SubMode:
    """Secondary capture modes grouped by primary mode.

    Video sub-modes:
        VIDEO, TIMELAPSE_VIDEO, VIDEO_PHOTO, LOOPING

    Photo sub-modes:
        SINGLE, NIGHT

    MultiShot sub-modes:
        BURST, TIMELAPSE, NIGHTLAPSE
    """

    # Video sub-modes
    VIDEO = 0
    TIMELAPSE_VIDEO = 1
    VIDEO_PHOTO = 2
    LOOPING = 3

    # Photo sub-modes
    SINGLE = 1
    NIGHT = 2

    # MultiShot sub-modes
    BURST = 0
    TIMELAPSE = 1
    NIGHTLAPSE = 2


class VideoResolution:
    """Video resolution setting IDs for /setting/2/<value>."""

    R4K = 1
    R2_7K = 4
    R2_7K_4_3 = 6
    R1440P = 7
    R1080P = 9
    R960P = 10
    R720P = 12
    RWVGA = 17


class FrameRate:
    """Frame rate setting IDs for /setting/3/<value>."""

    F240 = 0
    F120 = 1
    F100 = 2
    F90 = 3
    F80 = 4
    F60 = 5
    F50 = 6
    F48 = 7
    F30 = 8
    F25 = 9


class FieldOfView:
    """FOV setting IDs for /setting/4/<value>."""

    WIDE = 0
    MEDIUM = 1
    NARROW = 2
    SUPERVIEW = 3
    LINEAR = 4


@dataclass(frozen=True)
class CameraState:
    """Simplified camera state extracted from /status."""

    mode: int
    sub_mode: int
    recording: bool
    battery_level: Optional[int]
    remaining_space_bytes: Optional[int]
    sd_card_present: Optional[bool]


class GoPro:
    """High-level controller validated against KonradIT HERO5 docs."""

    def __init__(
        self,
        client: Optional[GoProClient] = None,
        *,
        host: str = DEFAULT_HOST,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.client = client or GoProClient(
            host=host, timeout=timeout, retries=retries
        )

    # --- Basic controls ---

    def shutter(self, start: bool = True) -> None:
        """Start or stop recording / timelapse capture."""
        self.client.get("/command/shutter", params={"p": 1 if start else 0})

    def set_mode(self, mode: int) -> None:
        """Set primary capture mode (Video, Photo or MultiShot)."""
        if mode not in (Mode.VIDEO, Mode.PHOTO, Mode.MULTISHOT):
            raise GoProError(f"Invalid primary mode: {mode}")
        self.client.get("/command/mode", params={"p": mode})

    def set_sub_mode(self, mode: int, sub_mode: int) -> None:
        """Set secondary capture mode."""
        self.client.get(
            "/command/sub_mode",
            params={"mode": mode, "sub_mode": sub_mode},
        )

    def power_off(self) -> None:
        """Put the camera to sleep."""
        self.client.get("/command/system/sleep")

    def locate(self, on: bool = True) -> None:
        """Enable or disable the locate beep."""
        self.client.get("/command/system/locate", params={"p": 1 if on else 0})

    def tag_moment(self) -> None:
        """Add a HiLight tag during recording."""
        self.client.get("/command/storage/tag_moment")

    # --- Settings ---

    def set_video_resolution(self, resolution: int) -> None:
        """Set video resolution via setting 2."""
        self.client.get(f"/setting/2/{resolution}")

    def set_frame_rate(self, fps: int) -> None:
        """Set video frame rate via setting 3."""
        self.client.get(f"/setting/3/{fps}")

    def set_fov(self, fov: int) -> None:
        """Set field of view via setting 4."""
        self.client.get(f"/setting/4/{fov}")

    def set_setting(self, setting_id: int, value: int) -> None:
        """Generic setting setter; the camera validates the value."""
        self.client.get(f"/setting/{setting_id}/{value}")

    # --- Status ---

    def status(self) -> dict[str, Any]:
        """Return raw status and settings JSON."""
        return self.client.status()

    def state(self) -> CameraState:
        """Return a simplified, typed camera state.

        Status field meanings are documented in HERO4/CameraStatus.md from
        KonradIT/goprowifihack and apply to HERO5 Black as well.
        """
        raw = self.status()
        status = raw.get("status", {})
        sd = status.get("33")
        return CameraState(
            mode=status.get("43", -1),
            sub_mode=status.get("44", -1),
            recording=bool(status.get("8", 0)),
            battery_level=status.get("2"),
            remaining_space_bytes=status.get("54"),
            sd_card_present=None if sd is None else (sd == 0),
        )

    def wake(self, mac: str, *, broadcast: str = "10.5.5.255", port: int = 9) -> None:
        """Power on the camera using Wake-on-LAN."""
        self.client.wake_on_lan(mac, broadcast=broadcast, port=port)

    def pair(self, device_name: str = "DESKTOP") -> None:
        """Complete pairing with the camera after connecting to its Wi-Fi.

        Endpoint documented for Hero 5 Black/Session:
        /gp/gpControl/command/wireless/pair/complete?success=1&deviceName=...
        """
        self.client.get(
            "/command/wireless/pair/complete",
            params={"success": 1, "deviceName": device_name},
        )
