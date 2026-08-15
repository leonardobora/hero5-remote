"""Tests for high-level camera commands."""

from unittest.mock import MagicMock, patch

import pytest

from hero5_remote.commands import FrameRate, GoPro, Mode, SubMode, VideoResolution
from hero5_remote.exceptions import GoProError


@pytest.fixture
def gopro():
    client = MagicMock()
    return GoPro(client=client)


class TestBasicControls:
    def test_shutter_start(self, gopro):
        gopro.shutter(start=True)
        gopro.client.get.assert_called_once_with(
            "/command/shutter", params={"p": 1}
        )

    def test_shutter_stop(self, gopro):
        gopro.shutter(start=False)
        gopro.client.get.assert_called_once_with(
            "/command/shutter", params={"p": 0}
        )

    def test_set_mode_video(self, gopro):
        gopro.set_mode(Mode.VIDEO)
        gopro.client.get.assert_called_once_with("/command/mode", params={"p": 0})

    def test_set_mode_invalid(self, gopro):
        with pytest.raises(GoProError):
            gopro.set_mode(99)

    def test_set_sub_mode(self, gopro):
        gopro.set_sub_mode(Mode.VIDEO, SubMode.TIMELAPSE_VIDEO)
        gopro.client.get.assert_called_once_with(
            "/command/sub_mode",
            params={"mode": 0, "sub_mode": 1},
        )

    def test_power_off(self, gopro):
        gopro.power_off()
        gopro.client.get.assert_called_once_with("/command/system/sleep")

    def test_locate_on(self, gopro):
        gopro.locate(on=True)
        gopro.client.get.assert_called_once_with(
            "/command/system/locate", params={"p": 1}
        )

    def test_tag_moment(self, gopro):
        gopro.tag_moment()
        gopro.client.get.assert_called_once_with("/command/storage/tag_moment")


class TestSettings:
    def test_set_video_resolution(self, gopro):
        gopro.set_video_resolution(VideoResolution.R1080P)
        gopro.client.get.assert_called_once_with("/setting/2/9")

    def test_set_frame_rate(self, gopro):
        gopro.set_frame_rate(FrameRate.F30)
        gopro.client.get.assert_called_once_with("/setting/3/8")

    def test_set_generic_setting(self, gopro):
        gopro.set_setting(62, 1_000_000)
        gopro.client.get.assert_called_once_with("/setting/62/1000000")


class TestState:
    def test_state_extraction(self):
        client = MagicMock()
        client.status.return_value = {
            "status": {
                "8": 1,
                "2": 3,
                "43": 0,
                "44": 0,
                "54": 12345,
                "33": 0,
            }
        }
        gopro = GoPro(client=client)
        state = gopro.state()
        assert state.recording is True
        assert state.battery_level == 3
        assert state.mode == 0
        assert state.sub_mode == 0
        assert state.remaining_space_bytes == 12345
        assert state.sd_card_present is True

    def test_state_missing_sd_flag(self):
        client = MagicMock()
        client.status.return_value = {"status": {"8": 0}}
        gopro = GoPro(client=client)
        state = gopro.state()
        assert state.sd_card_present is None
