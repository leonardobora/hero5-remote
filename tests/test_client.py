"""Tests for the low-level GoPro HTTP client."""

import json
import socket
from unittest.mock import MagicMock, patch

import pytest
import requests

from hero5_remote.client import DEFAULT_HOST, GoProClient
from hero5_remote.exceptions import (
    GoProConnectionError,
    GoProResponseError,
    GoProTimeoutError,
)


def _make_response(status_code: int = 200, text: str = "{}") -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = text.encode()
    return response


class TestGoProClient:
    def test_default_urls(self):
        client = GoProClient()
        assert client.control_url == f"http://{DEFAULT_HOST}/gp/gpControl"
        assert client.media_url == f"http://{DEFAULT_HOST}:8080"

    def test_status_parses_json(self):
        payload = {"status": {"1": 1}, "settings": {"2": 9}}
        client = GoProClient()
        with patch.object(client._session, "request") as mock_request:
            mock_request.return_value = _make_response(text=json.dumps(payload))
            assert client.status() == payload
            mock_request.assert_called_once_with(
                "GET",
                f"http://{DEFAULT_HOST}/gp/gpControl/status",
                timeout=client.timeout,
            )

    def test_status_invalid_json_raises(self):
        client = GoProClient()
        with patch.object(client._session, "request") as mock_request:
            mock_request.return_value = _make_response(text="not json")
            with pytest.raises(GoProResponseError):
                client.status()

    def test_http_error_raises_response_error(self):
        client = GoProClient(retries=1)
        with patch.object(client._session, "request") as mock_request:
            mock_request.return_value = _make_response(
                status_code=500, text="server error"
            )
            with pytest.raises(GoProResponseError):
                client.get("/command/shutter", params={"p": 1})

    def test_timeout_retries_then_raises(self):
        client = GoProClient(retries=2, timeout=0.1)
        with patch.object(client._session, "request") as mock_request:
            mock_request.side_effect = requests.Timeout("timed out")
            with pytest.raises(GoProTimeoutError):
                client.get("/status")
            assert mock_request.call_count == 2

    def test_connection_error_retries_then_raises(self):
        client = GoProClient(retries=3, timeout=0.1)
        with patch.object(client._session, "request") as mock_request:
            mock_request.side_effect = requests.ConnectionError("refused")
            with pytest.raises(GoProConnectionError):
                client.get("/status")
            assert mock_request.call_count == 3

    def test_eventual_success_after_retry(self):
        payload = {"status": {"8": 1}}
        client = GoProClient(retries=3)
        with patch.object(client._session, "request") as mock_request:
            mock_request.side_effect = [
                requests.Timeout("timed out"),
                _make_response(text=json.dumps(payload)),
            ]
            assert client.status() == payload
            assert mock_request.call_count == 2

    def test_wake_on_lan_sends_magic_packet(self):
        client = GoProClient()
        with patch("hero5_remote.client.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            client.wake_on_lan("aa:bb:cc:dd:ee:ff")
            mock_sock.setsockopt.assert_called_once_with(
                socket.SOL_SOCKET, socket.SO_BROADCAST, 1
            )
            sent = mock_sock.sendto.call_args[0]
            assert sent[1] == ("10.5.5.255", 9)
            assert len(sent[0]) == 6 + 16 * 6  # 6 sync + 16 repetitions of 6-byte MAC

    def test_wake_on_lan_rejects_invalid_mac(self):
        client = GoProClient()
        with pytest.raises(ValueError):
            client.wake_on_lan("not-a-mac")
