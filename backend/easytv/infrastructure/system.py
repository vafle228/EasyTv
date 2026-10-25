from __future__ import annotations

import socket
import uuid
from datetime import UTC, datetime

from easytv.core.models import Tv, Video


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidGenerator:
    def new_id(self) -> str:
        return uuid.uuid4().hex[:12]


class LanMediaUrlResolver:
    """Builds the URL a TV uses to download a video from this server.

    In Docker the server can't see the host's LAN address, so `public_host` must be given
    (run.sh detects it). Without it we pick the local address that routes to the TV.
    """

    def __init__(self, public_host: str | None, public_port: int) -> None:
        self._host = public_host
        self._port = public_port

    def url_for(self, video: Video, tv: Tv) -> str:
        return self.url_for_path(f"/media/{video.id}{video.extension}", tv)

    def url_for_path(self, path: str, tv: Tv) -> str:
        host = self._host or self._local_address_towards(tv.ip)
        return f"http://{host}:{self._port}{path}"

    @staticmethod
    def _local_address_towards(ip: str) -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((ip, 9))  # no packet is sent for UDP connect
            return s.getsockname()[0]
