"""Composition root: wires infrastructure adapters into core use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from easytv.config import Settings
from easytv.core.catalog import CatalogService, CinemaService
from easytv.core.ports import (
    CatalogSource,
    Clock,
    FileFetcher,
    IdGenerator,
    TvController,
    TvDiscovery,
    TvLocator,
    VideoDownloader,
)
from easytv.core.services import PlaybackService, TvService, VideoLibrary
from easytv.infrastructure.repositories import JsonSavedTitleRepository, JsonTvRepository, JsonVideoRepository
from easytv.infrastructure.storage import LocalVideoStorage
from easytv.infrastructure.system import LanMediaUrlResolver, SystemClock, UuidGenerator


@dataclass
class Container:
    settings: Settings
    tvs: TvService
    library: VideoLibrary
    playback: PlaybackService
    catalog: CatalogService
    cinema: CinemaService


def build_container(
    settings: Settings,
    *,
    discovery: TvDiscovery | None = None,
    locator: TvLocator | None = None,
    controller: TvController | None = None,
    downloader: VideoDownloader | None = None,
    catalog_source: CatalogSource | None = None,
    fetcher: FileFetcher | None = None,
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
    if catalog_source is None:
        from easytv.infrastructure.animego import AnimegoCatalog

        catalog_source = AnimegoCatalog(base_url=settings.animego_url)
    if fetcher is None:
        from easytv.infrastructure.fetch import HttpFileFetcher

        fetcher = HttpFileFetcher()
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
    library = VideoLibrary(
        JsonVideoRepository(settings.data_dir / "videos.json"), storage, downloader, clock, ids, fetcher
    )
    catalog = CatalogService(catalog_source, clock, settings.max_video_height)
    cinema = CinemaService(JsonSavedTitleRepository(settings.data_dir / "cinema.json"), catalog, clock)
    urls = LanMediaUrlResolver(settings.public_host, settings.advertised_port)
    playback = PlaybackService(tvs, library, controller, urls, catalog)
    return Container(
        settings=settings, tvs=tvs, library=library, playback=playback, catalog=catalog, cinema=cinema
    )
