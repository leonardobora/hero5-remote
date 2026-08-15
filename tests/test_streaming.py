"""Tests for the streaming module."""

from unittest.mock import MagicMock, patch

import pytest

from hero5_remote.commands import Mode, SubMode
from hero5_remote.streaming import (
    StreamController,
    StreamingError,
    _build_udp_url,
    _find_gopro_local_ip,
)


@pytest.fixture
def controller():
    client = MagicMock()
    gopro = MagicMock()
    gopro.client = client
    return StreamController(gopro)


class TestStreamControl:
    def test_start_camera_stream(self, controller):
        controller.start_camera_stream()
        controller.gopro.client.get.assert_called_once_with(
            "/execute",
            params={"p1": "gpStream", "a1": "proto_v2", "c1": "restart"},
        )

    def test_stop_camera_stream_changes_mode(self, controller):
        controller.stop_camera_stream()
        controller.gopro.set_mode.assert_called_once_with(Mode.VIDEO)
        controller.gopro.set_sub_mode.assert_called_once_with(Mode.VIDEO, SubMode.VIDEO)

    def test_set_bitrate(self, controller):
        controller.set_bitrate(1_000_000)
        controller.gopro.set_setting.assert_called_once_with(62, 1_000_000)

    def test_set_window_size(self, controller):
        controller.set_window_size(7)
        controller.gopro.set_setting.assert_called_once_with(64, 7)


class TestVirtualCamera:
    def test_build_ffmpeg_command_requires_ffmpeg(self, controller):
        with patch("hero5_remote.streaming.shutil.which", return_value=None):
            with pytest.raises(StreamingError):
                controller._build_ffmpeg_command(1280, 720, 30, "udp://10.5.5.9:8554")

    def test_build_ffmpeg_command(self, controller):
        with patch("hero5_remote.streaming.shutil.which", return_value="/usr/bin/ffmpeg"):
            cmd = controller._build_ffmpeg_command(
                1280, 720, 30, "udp://10.5.5.9:8554"
            )
        assert cmd[0] == "/usr/bin/ffmpeg"
        assert "udp://10.5.5.9:8554" in cmd
        assert "-an" in cmd
        assert "-fflags" in cmd
        assert "-flags" in cmd
        assert any("scale=1280:720" in str(part) for part in cmd)

    def test_serve_virtual_camera_requires_ffmpeg(self, controller):
        with patch("hero5_remote.streaming.shutil.which", return_value=None):
            with pytest.raises(StreamingError):
                controller.serve_virtual_camera()


class TestUdpUrl:
    def test_build_udp_url_uses_local_ip(self):
        url = _build_udp_url("10.5.5.9", "10.5.5.100")
        assert url == "udp://10.5.5.9:8554?localaddr=10.5.5.100"

    def test_find_gopro_local_ip_raises_when_not_connected(self):
        with patch("hero5_remote.streaming.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.connect.side_effect = OSError("Network unreachable")
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            with pytest.raises(StreamingError):
                _find_gopro_local_ip("10.5.5.9")
