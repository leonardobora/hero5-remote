"""Example usage of hero5-remote as a library."""

import logging

from hero5_remote import GoPro, Mode, SubMode
from hero5_remote.media import Media

logging.basicConfig(level=logging.DEBUG)


def main() -> None:
    # Connect to the default GoPro Wi-Fi address.
    gopro = GoPro()

    # Fetch and print current state.
    print("State:", gopro.state())

    # Switch to video mode and start recording.
    gopro.set_mode(Mode.VIDEO)
    gopro.set_sub_mode(Mode.VIDEO, SubMode.VIDEO)
    gopro.shutter(start=True)

    # List media on the SD card.
    media = Media(gopro.client)
    print("Media list:", media.list())

    # Power off when done.
    gopro.power_off()


if __name__ == "__main__":
    main()
