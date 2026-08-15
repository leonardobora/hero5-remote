# hero5-remote

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Python remote control interface for the **GoPro Hero 5 Black** via Wi-Fi HTTP API.

Every command is validated against the [KonradIT/goprowifihack](https://github.com/KonradIT/goprowifihack/tree/master/HERO5) documentation. No endpoints are guessed or hallucinated.

## Scope

This project focuses on **remote control** over Wi-Fi:

- Start/stop recording
- Change capture modes and settings
- Read camera status
- Browse, inspect and delete media on the SD card
- Wake the camera over the network

Live video streaming is intentionally left out of the MVP because the Hero 5 Black only exposes a low-level UDP H.264 preview stream (`udp://10.5.5.9:8554`). Turning that into a usable webcam/RTMP source requires a separate transcoding pipeline. See [Streaming backlog](#streaming-backlog) below.

## Installation

```bash
git clone https://github.com/leonardobora/hero5-remote.git
cd hero5-remote
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Pairing

1. Power on the GoPro.
2. On the camera: **Connections > New > GoPro App**.
3. Connect your computer to the GoPro Wi-Fi network.
4. Complete pairing from your machine:

```bash
hero5-remote wake <camera-mac-address>
```

The camera MAC address can usually be found on the camera body or obtained from the ARP table after the first connection.

## CLI usage

```bash
# Status
hero5-remote status
hero5-remote state

# Recording
hero5-remote shutter --start
hero5-remote shutter --stop

# Modes
hero5-remote mode video
hero5-remote mode photo
hero5-remote mode multishot
hero5-remote sub-mode 0 1  # Video -> TimeLapse Video

# Power / locate
hero5-remote power-off
hero5-remote locate --on
hero5-remote wake aa:bb:cc:dd:ee:ff

# Media
hero5-remote media list
hero5-remote media info /100GOPRO/GOPR0001.MP4
hero5-remote media delete /100GOPRO/GOPR0001.JPG
hero5-remote media delete-last
```

Use `-v` for debug logging:

```bash
hero5-remote -v status
```

## Library usage

```python
from hero5_remote import GoPro, Mode, SubMode
from hero5_remote.media import Media

gopro = GoPro()
print(gopro.state())

gopro.set_mode(Mode.VIDEO)
gopro.set_sub_mode(Mode.VIDEO, SubMode.VIDEO)
gopro.shutter(start=True)

media = Media(gopro.client)
print(media.list())
```

## Project structure

```text
hero5-remote/
├── src/hero5_remote/
│   ├── client.py      # HTTP client with retries, timeouts, logging
│   ├── commands.py    # High-level camera operations
│   ├── media.py       # Media browsing and management
│   ├── cli.py         # Command-line interface
│   └── exceptions.py  # Typed errors
├── tests/             # pytest suite with mocked camera responses
└── scripts/           # Example usage
```

## Resilience

- All HTTP requests have explicit timeouts.
- Failed requests retry with exponential backoff.
- Distinct exceptions for connection, timeout and HTTP response errors.
- Verbose debug logging of every request and response.

## Streaming backlog

The Hero 5 Black can start a UDP preview stream with:

```bash
GET http://10.5.5.9/gp/gpControl/execute?p1=gpStream&a1=proto_v2&c1=restart
```

Stream URL: `udp://10.5.5.9:8554`

To make this consumable by other apps you will likely need `ffmpeg` to bridge it to a virtual camera (e.g., `v4l2loopback` on Linux) or to an RTMP/WebRTC server. This is tracked as future work.

## License

MIT
