from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _list(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").replace(";", ",").split(",") if item.strip()]


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 8080
    # Address/port TVs use to download videos from us (host LAN IP when running in Docker).
    public_host: str | None = None
    public_port: int | None = None
    data_dir: Path = Path("data")
    static_dir: Path | None = None
    discovery_interval_s: float = 15.0
    discovery_timeout_s: float = 3.0
    offline_after_s: float = 60.0
    # Unicast discovery: hosts probed directly and subnets swept every cycle (needed in Docker).
    tv_hosts: list[str] = field(default_factory=list)
    # Description URLs of TVs found by run.sh on the host machine (where multicast works).
    tv_locations: list[str] = field(default_factory=list)
    scan_subnets: list[str] = field(default_factory=list)
    max_video_height: int = 1080

    @property
    def seeds(self) -> list[str]:
        return list(dict.fromkeys(self.tv_locations + self.tv_hosts))

    @property
    def advertised_port(self) -> int:
        return self.public_port or self.port

    @classmethod
    def from_env(cls) -> Settings:
        env = os.environ.get
        static = env("EASYTV_STATIC_DIR")
        return cls(
            host=env("EASYTV_HOST", "0.0.0.0"),
            port=int(env("EASYTV_PORT", "8080")),
            public_host=env("EASYTV_PUBLIC_HOST") or None,
            public_port=int(env("EASYTV_PUBLIC_PORT")) if env("EASYTV_PUBLIC_PORT") else None,
            data_dir=Path(env("EASYTV_DATA_DIR", "data")),
            static_dir=Path(static) if static else None,
            discovery_interval_s=float(env("EASYTV_DISCOVERY_INTERVAL", "15")),
            discovery_timeout_s=float(env("EASYTV_DISCOVERY_TIMEOUT", "3")),
            offline_after_s=float(env("EASYTV_OFFLINE_AFTER", "60")),
            tv_hosts=_list(env("EASYTV_TV_HOSTS")),
            tv_locations=_list(env("EASYTV_TV_LOCATIONS")),
            scan_subnets=_list(env("EASYTV_SCAN_SUBNETS")),
            max_video_height=int(env("EASYTV_MAX_VIDEO_HEIGHT", "1080")),
        )
