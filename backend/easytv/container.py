"""Composition root: wires infrastructure adapters into core use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from easytv.config import Settings
from easytv.core.ports import Clock, IdGenerator, TvController, TvDiscovery, TvLocator, VideoDownloader
from easytv.core.services import PlaybackService, TvService, VideoLibrary
from easytv.infrastructure.repositories import JsonTvRepository, JsonVideoRepository
from easytv.infrastructure.storage import LocalVideoStorage
from easytv.infrastructure.system import LanMediaUrlResolver, SystemClock, UuidGenerator


@dataclass
class Container:
    settings: Settings
    tvs: TvService
    library: VideoLibrary
    playback: PlaybackService


def build_container(
    settings: Settings,
    *,
    discovery: TvDiscovery | None = None,
    locator: TvLocator | None = None,
    controller: TvController | None = None,
    downloader: VideoDownloader | None = None,
    clock: Clock | None = None,
    ids: IdGenerator | None = None,
) -> Container:
    """Real adapters by default; tests pass fakes for the network-facing ports."""
    if discovery is None:
        from easytv.infrastructure.upnp import SsdpTvDiscovery

        discovery = SsdpTvDiscovery(settings.tv_hosts, settings.scan_subnets, settings.discovery_timeout_s)
    if locator is None:
        from easytv.infrastructure.upnp import UpnpTvLocator

        locator = UpnpTvLocator()
    if controller is None:
        from easytv.infrastructure.upnp import UpnpTvController

        controller = UpnpTvController()
    if downloader is None:
        from easytv.infrastructure.ytdlp import YtDlpDownloader

        downloader = YtDlpDownloader(settings.max_video_height)
    clock = clock or SystemClock()
    ids = ids or UuidGenerator()

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    storage = LocalVideoStorage(settings.data_dir / "videos")
    tvs = TvService(
        discovery,
        locator,
        JsonTvRepository(settings.data_dir / "tvs.json"),
        clock,
        timedelta(seconds=settings.offline_after_s),
        seeds=settings.seeds,
    )
    library = VideoLibrary(JsonVideoRepository(settings.data_dir / "videos.json"), storage, downloader, clock, ids)
    urls = LanMediaUrlResolver(settings.public_host, settings.advertised_port)
    playback = PlaybackService(tvs, library, controller, urls)
    return Container(settings=settings, tvs=tvs, library=library, playback=playback)
