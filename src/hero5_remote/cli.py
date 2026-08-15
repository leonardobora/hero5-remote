"""Command-line interface for hero5-remote."""

import argparse
import json
import logging
import sys
from typing import Sequence

from . import __version__
from .client import DEFAULT_HOST
from .commands import FrameRate, FieldOfView, GoPro, Mode, SubMode, VideoResolution
from .exceptions import GoProError
from .media import Media
from .streaming import StreamController, StreamingError


def _add_camera_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"GoPro IP address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5,
        help="Request timeout in seconds (default: 5)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Number of retries per request (default: 3)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )


def _build_camera(args: argparse.Namespace) -> GoPro:
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    return GoPro(host=args.host, timeout=args.timeout, retries=args.retries)


def _media(args: argparse.Namespace) -> Media:
    camera = _build_camera(args)
    return Media(camera.client)


def cmd_status(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    print(json.dumps(camera.status(), indent=2))
    return 0


def cmd_state(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    state = camera.state()
    print(json.dumps(state.__dict__, indent=2))
    return 0


def cmd_shutter(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    camera.shutter(start=args.start)
    print("Recording started." if args.start else "Recording stopped.")
    return 0


def cmd_mode(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    mode_map = {
        "video": Mode.VIDEO,
        "photo": Mode.PHOTO,
        "multishot": Mode.MULTISHOT,
    }
    camera.set_mode(mode_map[args.mode])
    print(f"Mode set to {args.mode}.")
    return 0


def cmd_sub_mode(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    camera.set_sub_mode(args.mode, args.sub_mode)
    print(f"Sub-mode set to mode={args.mode} sub_mode={args.sub_mode}.")
    return 0


def cmd_power_off(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    camera.power_off()
    print("Camera powered off.")
    return 0


def cmd_wake(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    camera.wake(args.mac, broadcast=args.broadcast, port=args.port)
    print(f"Wake-on-LAN sent to {args.mac}.")
    return 0


def cmd_locate(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    camera.locate(on=args.on)
    print("Locate beep enabled." if args.on else "Locate beep disabled.")
    return 0


def cmd_tag(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    camera.tag_moment()
    print("Moment tagged.")
    return 0


def cmd_setting(args: argparse.Namespace) -> int:
    camera = _build_camera(args)
    camera.set_setting(args.setting_id, args.value)
    print(f"Setting {args.setting_id} set to {args.value}.")
    return 0


def cmd_media_list(args: argparse.Namespace) -> int:
    media = _media(args)
    print(json.dumps(media.list(), indent=2))
    return 0


def cmd_media_info(args: argparse.Namespace) -> int:
    media = _media(args)
    info = media.detailed_info(args.path)
    print(json.dumps(info, indent=2))
    return 0


def cmd_media_delete(args: argparse.Namespace) -> int:
    media = _media(args)
    media.delete(args.path)
    print(f"Deleted {args.path}.")
    return 0


def cmd_media_delete_last(args: argparse.Namespace) -> int:
    media = _media(args)
    media.delete_last()
    print("Last media deleted.")
    return 0


def cmd_stream_start(args: argparse.Namespace) -> int:
    controller = StreamController(_build_camera(args))
    controller.start_camera_stream()
    print("GoPro preview stream started. Feed available at udp://10.5.5.9:8554")
    return 0


def cmd_stream_stop(args: argparse.Namespace) -> int:
    controller = StreamController(_build_camera(args))
    controller.stop_camera_stream()
    print("GoPro preview stream stopped.")
    return 0


def cmd_stream_bitrate(args: argparse.Namespace) -> int:
    controller = StreamController(_build_camera(args))
    controller.set_bitrate(args.bps)
    print(f"Stream bitrate set to {args.bps} bps.")
    return 0


def cmd_stream_window(args: argparse.Namespace) -> int:
    controller = StreamController(_build_camera(args))
    controller.set_window_size(args.size_id)
    print(f"Stream window size set to {args.size_id}.")
    return 0


def cmd_stream_virtual_camera(args: argparse.Namespace) -> int:
    controller = StreamController(_build_camera(args))
    controller.start_camera_stream()
    print("Starting virtual camera bridge... Press Ctrl+C to stop.")
    try:
        controller.serve_virtual_camera(
            width=args.width,
            height=args.height,
            fps=args.fps,
        )
    except KeyboardInterrupt:
        controller.stop()
        controller.stop_camera_stream()
        print("\nVirtual camera stopped.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hero5-remote",
        description="Remote control for GoPro Hero 5 Black via Wi-Fi.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = sub.add_parser("status", help="Fetch raw camera status")
    _add_camera_args(p_status)
    p_status.set_defaults(func=cmd_status)

    # state
    p_state = sub.add_parser("state", help="Fetch simplified camera state")
    _add_camera_args(p_state)
    p_state.set_defaults(func=cmd_state)

    # shutter
    p_shutter = sub.add_parser("shutter", help="Start or stop recording")
    _add_camera_args(p_shutter)
    p_shutter.add_argument(
        "--start",
        dest="start",
        action="store_true",
        help="Start recording",
    )
    p_shutter.add_argument(
        "--stop",
        dest="start",
        action="store_false",
        help="Stop recording",
    )
    p_shutter.set_defaults(func=cmd_shutter, start=True)

    # mode
    p_mode = sub.add_parser("mode", help="Set primary capture mode")
    _add_camera_args(p_mode)
    p_mode.add_argument(
        "mode",
        choices=["video", "photo", "multishot"],
        help="Capture mode",
    )
    p_mode.set_defaults(func=cmd_mode)

    # sub-mode
    p_sub = sub.add_parser("sub-mode", help="Set secondary capture mode")
    _add_camera_args(p_sub)
    p_sub.add_argument("mode", type=int, help="Primary mode ID")
    p_sub.add_argument("sub_mode", type=int, help="Sub-mode ID")
    p_sub.set_defaults(func=cmd_sub_mode)

    # power-off
    p_off = sub.add_parser("power-off", help="Power off the camera")
    _add_camera_args(p_off)
    p_off.set_defaults(func=cmd_power_off)

    # wake
    p_wake = sub.add_parser("wake", help="Wake the camera via WoL")
    p_wake.add_argument("mac", help="Camera MAC address")
    p_wake.add_argument(
        "--broadcast",
        default="10.5.5.255",
        help="Broadcast address (default: 10.5.5.255)",
    )
    p_wake.add_argument(
        "--port",
        type=int,
        default=9,
        help="WoL UDP port (default: 9)",
    )
    _add_camera_args(p_wake)
    p_wake.set_defaults(func=cmd_wake)

    # locate
    p_loc = sub.add_parser("locate", help="Enable or disable locate beep")
    _add_camera_args(p_loc)
    p_loc.add_argument(
        "--on",
        dest="on",
        action="store_true",
        help="Enable locate beep",
    )
    p_loc.add_argument(
        "--off",
        dest="on",
        action="store_false",
        help="Disable locate beep",
    )
    p_loc.set_defaults(func=cmd_locate, on=True)

    # tag
    p_tag = sub.add_parser("tag", help="Tag a moment during recording")
    _add_camera_args(p_tag)
    p_tag.set_defaults(func=cmd_tag)

    # setting
    p_set = sub.add_parser("setting", help="Set a generic camera setting")
    _add_camera_args(p_set)
    p_set.add_argument("setting_id", type=int, help="Setting ID")
    p_set.add_argument("value", type=int, help="Setting value")
    p_set.set_defaults(func=cmd_setting)

    # media
    p_media = sub.add_parser("media", help="Media management")
    media_sub = p_media.add_subparsers(dest="media_command", required=True)

    p_list = media_sub.add_parser("list", help="List media on SD card")
    _add_camera_args(p_list)
    p_list.set_defaults(func=cmd_media_list)

    p_info = media_sub.add_parser("info", help="Show detailed media info")
    _add_camera_args(p_info)
    p_info.add_argument("path", help="Media path, e.g. /100GOPRO/GOPR0001.MP4")
    p_info.set_defaults(func=cmd_media_info)

    p_del = media_sub.add_parser("delete", help="Delete a media file")
    _add_camera_args(p_del)
    p_del.add_argument("path", help="Media path, e.g. /100GOPRO/GOPR0001.JPG")
    p_del.set_defaults(func=cmd_media_delete)

    p_del_last = media_sub.add_parser(
        "delete-last", help="Delete the last captured media"
    )
    _add_camera_args(p_del_last)
    p_del_last.set_defaults(func=cmd_media_delete_last)

    # stream
    p_stream = sub.add_parser("stream", help="Live preview streaming")
    stream_sub = p_stream.add_subparsers(dest="stream_command", required=True)

    p_stream_start = stream_sub.add_parser(
        "start", help="Start the GoPro UDP preview stream"
    )
    _add_camera_args(p_stream_start)
    p_stream_start.set_defaults(func=cmd_stream_start)

    p_stream_stop = stream_sub.add_parser(
        "stop", help="Stop the GoPro UDP preview stream"
    )
    _add_camera_args(p_stream_stop)
    p_stream_stop.set_defaults(func=cmd_stream_stop)

    p_stream_bitrate = stream_sub.add_parser(
        "bitrate", help="Set stream bitrate (setting 62)"
    )
    _add_camera_args(p_stream_bitrate)
    p_stream_bitrate.add_argument("bps", type=int, help="Bitrate in bits per second")
    p_stream_bitrate.set_defaults(func=cmd_stream_bitrate)

    p_stream_window = stream_sub.add_parser(
        "window", help="Set stream window size (setting 64)"
    )
    _add_camera_args(p_stream_window)
    p_stream_window.add_argument("size_id", type=int, help="Window size ID")
    p_stream_window.set_defaults(func=cmd_stream_window)

    p_stream_cam = stream_sub.add_parser(
        "virtual-camera",
        help="Bridge the UDP stream to a virtual camera (Windows + OBS driver)",
    )
    _add_camera_args(p_stream_cam)
    p_stream_cam.add_argument("--width", type=int, default=1280)
    p_stream_cam.add_argument("--height", type=int, default=720)
    p_stream_cam.add_argument("--fps", type=int, default=30)
    p_stream_cam.set_defaults(func=cmd_stream_virtual_camera)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except GoProError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
