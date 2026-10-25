"""animego.me as a `CatalogSource`: search, title card, episodes, dubs and fresh direct links."""

from __future__ import annotations

from easytv.core.errors import CatalogItemNotFound
from easytv.core.models import CatalogTitle, Episode, Stream, StreamRef, TitleDetails, TitleKind, Variant

from .client import (
    DEFAULT_BASE_URL,
    SUPPORTED_PROVIDERS,
    AnimeGo,
    AnimeGoError,
    Http,
    RawStream,
    Resolver,
    rank_options,
)

__all__ = ["AnimegoCatalog", "Http"]


class AnimegoCatalog:
    name = "animego"

    def __init__(self, http: Http | None = None, base_url: str = DEFAULT_BASE_URL) -> None:
        self._http = http or Http()
        self._site = AnimeGo(self._http, base_url)
        self._resolver = Resolver(self._http, base_url)

    def search(self, query: str) -> list[CatalogTitle]:
        return [
            CatalogTitle(
                id=r.title_id,
                title=r.title,
                original_title=r.original_title,
                kind=r.kind,
                year=r.year,
                rating=r.rating,
                poster=r.poster,
                url=r.url,
            )
            for r in self._site.search(query)
        ]

    def title(self, title_id: str) -> TitleDetails:
        i = self._site.info(title_id)
        return TitleDetails(
            id=title_id,
            title=i.title,
            kind=TitleKind.MOVIE if i.kind == "movie" else TitleKind.SERIES,
            url=i.url,
            original_title=i.alternate_name,
            description=i.description,
            poster=i.poster,
            genres=tuple(i.genres),
            year=(i.date_published or "")[:4] or None,
            episodes_total=i.episodes_total,
            rating=i.rating,
            studio=i.studio,
        )

    def episodes(self, title_id: str) -> list[Episode]:
        return [Episode(number=e.number, title=e.title, date=e.release_date) for e in self._site.episodes(title_id)]

    def variants(self, title_id: str, episode: int) -> list[Variant]:
        grouped: dict[str, tuple[str, list[str]]] = {}
        for o in rank_options(self._site.players(title_id, episode)):
            if o.provider not in SUPPORTED_PROVIDERS:
                continue
            name, providers = grouped.setdefault(o.translation_id, (o.translation, []))
            if o.provider not in providers:
                providers.append(o.provider)
        return [Variant(translation_id=k, translation=name, providers=tuple(p)) for k, (name, p) in grouped.items()]

    def streams(self, ref: StreamRef) -> list[Stream]:
        options = [o for o in self._site.players(ref.title_id, ref.episode) if o.translation_id == ref.translation_id]
        if ref.provider != "auto":
            options = [o for o in options if o.provider == ref.provider]
        if not options:
            raise CatalogItemNotFound("на animego нет такой озвучки у этой серии")
        fallback: list[RawStream] = []
        errors: list[str] = []
        for opt in rank_options(options):
            try:
                found = self._resolver.resolve(opt)
            except AnimeGoError as e:
                errors.append(f"{opt.provider_title}: {e}")
                continue
            if any(s.kind == "mp4" for s in found):
                return [_stream(s) for s in found]
            fallback = fallback or found
        if fallback:
            return [_stream(s) for s in fallback]
        raise AnimeGoError("ни один плеер не отдал ссылку. " + "; ".join(errors))


def _stream(s: RawStream) -> Stream:
    return Stream(provider=s.provider, translation=s.translation, kind=s.kind, quality=s.quality, url=s.url, headers=s.headers)
