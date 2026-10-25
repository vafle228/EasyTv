"""AnimeGo and its players (CVH, Kodik, Aniboom), ported from the research script `animego/animego_probe.py`.

Map of requests and the findings behind every step: `animego/animego-findings.md` in the project files.
Parsers are pure functions over saved pages, so `tests/test_animego.py` checks them on fixtures from the live site.
"""

from __future__ import annotations

import base64
import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlparse

import httpx

from easytv.core.errors import CatalogError, CatalogItemNotFound

from .dom import Node, parse_html

DEFAULT_BASE_URL = "https://animego.me"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
CVH_API = "https://plapi.cdnvideohub.com/api/v1/player/sv"
KODIK_FALLBACK_ENDPOINT = "/ftor"
CHALLENGE_RE = re.compile(r"<title>\s*(DDoS-Guard|Just a moment|Attention Required)|Checking your browser", re.I)
# The player posts only the signed part of urlParams to /ftor (function h() in app.player_single.js).
KODIK_SIGNED_KEYS = ("d", "d_sign", "pd", "pd_sign", "ref", "ref_sign")
# Direct mp4 beats HLS for DLNA TVs.
PROVIDER_PRIORITY = ("cvh", "kodik", "aniboom")
SUPPORTED_PROVIDERS = frozenset(PROVIDER_PRIORITY)
CVH_QUALITIES = {
    "mpeg4kUrl": 2160, "mpeg2kUrl": 1440, "mpegQhdUrl": 1440,
    "mpegFullHdUrl": 1080, "mpegHighUrl": 720, "mpegMediumUrl": 480,
    "mpegLowUrl": 360, "mpegLowestUrl": 240, "mpegTinyUrl": 144,
}  # fmt: skip
ANIME_URL_RE = re.compile(r"/anime/([^/?#]+-(\d+))/?(?:[?#].*)?$")
TITLE_ID_RE = re.compile(r"^[\w-]+-(\d+)$")


# ---- errors


class AnimeGoError(CatalogError):
    pass


class NotFound(AnimeGoError, CatalogItemNotFound):
    pass


class LayoutChanged(AnimeGoError):
    """The site or a player changed its markup: an expected block is gone."""

    def __init__(self, where: str, what: str) -> None:
        super().__init__(f"animego, {where}: не найден {what}. Похоже, сайт поменял вёрстку")


class Blocked(AnimeGoError):
    pass


class UnsupportedPlayer(AnimeGoError):
    pass


# ---- raw site data


@dataclass
class SearchResult:
    anime_id: int
    title_id: str
    title: str
    original_title: str | None
    kind: str | None
    year: str | None
    rating: str | None
    poster: str | None
    url: str


@dataclass
class TitleInfo:
    anime_id: int
    url: str
    title: str
    kind: str | None
    alternate_name: str | None
    description: str | None
    poster: str | None
    genres: list[str]
    date_published: str | None
    episodes_total: int | None
    rating: float | None
    studio: str | None


@dataclass
class EpisodeInfo:
    number: int
    episode_id: int | None
    title: str | None = None
    release_date: str | None = None


@dataclass
class PlayerOption:
    provider: str  # cvh / kodik / aniboom / ...
    provider_title: str
    translation_id: str
    translation: str
    embed_url: str


@dataclass
class RawStream:
    provider: str
    translation: str
    kind: str  # mp4 / hls / dash
    quality: int | None
    url: str
    headers: dict[str, str] = field(default_factory=dict)


# ---- HTTP


class Http:
    """httpx client with a pause between requests to the same site and a small in-memory cache."""

    def __init__(self, delay: float = 0.3, cache_ttl: float = 600, timeout: float = 20) -> None:
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"},
            timeout=timeout,
            follow_redirects=True,
        )
        self.delay = delay
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()
        self._last = 0.0

    def _sleep(self) -> None:
        with self._lock:
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def request(self, method: str, url: str, *, cache: bool = False, **kw: Any) -> str:
        key = method + " " + url + " " + json.dumps(kw.get("data") or {}, sort_keys=True)
        if cache and (hit := self._cache.get(key)) and time.monotonic() - hit[0] < self.cache_ttl:
            return hit[1]
        self._sleep()
        try:
            r = self.client.request(method, url, **kw)
        except httpx.HTTPError as e:
            raise AnimeGoError(f"animego не отвечает ({urlparse(url).hostname}): {e or e.__class__.__name__}") from e
        if r.status_code == 404:
            raise NotFound(f"404: {url}")
        if r.status_code in (403, 429, 503):
            raise Blocked(f"{urlparse(url).hostname} ответил {r.status_code}: защита, капча или лимит запросов")
        if r.status_code >= 400:
            raise AnimeGoError(f"{urlparse(url).hostname} ответил {r.status_code}")
        text = r.text
        if CHALLENGE_RE.search(text[:3000]):
            raise Blocked(f"{urlparse(url).hostname} показал страницу проверки браузера (DDoS-Guard)")
        if cache:
            self._cache[key] = (time.monotonic(), text)
        return text

    def get(self, url: str, **kw: Any) -> str:
        return self.request("GET", url, **kw)

    def get_json(self, url: str, **kw: Any) -> Any:
        text = self.get(url, **kw)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LayoutChanged(urlparse(url).path, "JSON в ответе") from e

    def post(self, url: str, **kw: Any) -> str:
        return self.request("POST", url, **kw)


def _abs(url: str) -> str:
    return "https:" + url if url.startswith("//") else url


def anime_id_of(title_id: str) -> int:
    m = TITLE_ID_RE.match(title_id)
    if not m:
        raise NotFound(f"не понимаю id тайтла: {title_id!r}")
    return int(m.group(1))


# ---- AnimeGo


class AnimeGo:
    XHR = {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}

    def __init__(self, http: Http, base_url: str = DEFAULT_BASE_URL) -> None:
        self.http = http
        self.base = base_url.rstrip("/")

    def title_url(self, title_id: str) -> str:
        return f"{self.base}/anime/{title_id}"

    def search(self, query: str) -> list[SearchResult]:
        html = self.http.get(f"{self.base}/search/all?q={quote(query)}", cache=True)
        return parse_search(html, self.base)

    def info(self, title_id: str) -> TitleInfo:
        url = self.title_url(title_id)
        return parse_title_page(self.http.get(url, cache=True), anime_id_of(title_id), url)

    def _player_root(self, anime_id: int) -> Node:
        data = self.http.get_json(f"{self.base}/player/{anime_id}", headers=self.XHR, cache=True)
        return parse_html(_player_content(data, f"/player/{anime_id}"))

    def _player_episodes(self, anime_id: int, root: Node | None = None) -> list[EpisodeInfo]:
        """All episodes: the first hundred come with /player/{id}, the rest from /episodes?page=N."""
        root = root or self._player_root(anime_id)
        eps, pages = parse_player_episodes(root)
        for page in pages[1:]:
            data = self.http.get_json(
                f"{self.base}/player/{anime_id}/episodes?page={page}", headers=self.XHR, cache=True
            )
            more, _ = parse_player_episodes(parse_html(_player_content(data, "episodes")))
            eps.extend(more)
        return eps

    def episodes(self, title_id: str) -> list[EpisodeInfo]:
        eps = self._player_episodes(anime_id_of(title_id))
        if eps:
            try:
                titles = self._schedule(self.title_url(title_id))
            except AnimeGoError:
                titles = {}
            for ep in eps:
                if ep.number in titles:
                    ep.title, ep.release_date = titles[ep.number]
        return eps

    def _schedule(self, url: str) -> dict[int, tuple[str | None, str | None]]:
        """Episode names and dates from the schedule table on the title page."""
        page_html = self.http.get(url, cache=True)
        result = parse_schedule(page_html)
        template = parse_schedule_template(page_html)
        page = 1
        while template and page < 50:
            data = self.http.get_json(
                self.base + template.replace("__page__", str(page)), headers=self.XHR, cache=True
            )
            d = data.get("data") or {}
            chunk = parse_schedule(d.get("content") or "")
            result.update(chunk)
            if not chunk or d.get("endPage") is True:
                break
            page += 1
        return result

    def players(self, title_id: str, episode: int) -> list[PlayerOption]:
        """Players of an episode; `episode` is ignored for a movie (its players come with /player/{id})."""
        anime_id = anime_id_of(title_id)
        root = self._player_root(anime_id)
        eps, _ = parse_player_episodes(root)
        if not eps:
            return parse_providers(root)
        all_eps = eps if len(eps) < 100 else self._player_episodes(anime_id, root)
        ep = next((e for e in all_eps if e.number == episode), None)
        if not ep or not ep.episode_id:
            raise NotFound(f"серии {episode} нет на animego (всего серий: {len(all_eps)})")
        # The players in /player/{id} belong to the "active" episode of the session: always ask for this one.
        data = self.http.get_json(f"{self.base}/player/videos/{ep.episode_id}", headers=self.XHR, cache=True)
        options = parse_providers(parse_html(_player_content(data, "/player/videos")))
        if not options:
            raise NotFound(f"у серии {episode} пока нет видео")
        return options


def _player_content(data: Any, where: str) -> str:
    if not isinstance(data, dict) or data.get("status") != "success":
        raise LayoutChanged(where, "status=success")
    content = (data.get("data") or {}).get("content")
    if not isinstance(content, str):
        raise LayoutChanged(where, "data.content")
    return content


# ---- parsers (pure functions, tested on fixtures)


def parse_search(html: str, base: str) -> list[SearchResult]:
    out: list[SearchResult] = []
    for item in parse_html(html).select(".ani-grid__item"):
        a = item.select_one(".ani-grid__item-title a[href]")
        if not a:
            continue
        m = ANIME_URL_RE.search(a["href"])
        if not m:  # characters, people, manga
            continue
        body = item.select_one(".ani-grid__item-body")
        orig = None
        if body:
            first = body.first_element()
            if first and first.tag == "div" and "ani-grid__item-title" not in first.classes:
                orig = first.text() or None
        meta = [s.text() for s in item.select(".ani-grid__item-genres__link")]
        badge = item.select_one(".rating-badge")
        img = item.select_one("img[src]")
        out.append(
            SearchResult(
                anime_id=int(m.group(2)),
                title_id=m.group(1),
                title=a.get("title") or a.text(),
                original_title=orig,
                kind=meta[0] if meta else None,
                year=next((x for x in meta if re.fullmatch(r"\d{4}", x)), None),
                rating=badge.text() if badge else None,
                poster=_abs(img["src"]) if img else None,
                url=urljoin(base + "/", a["href"]),
            )
        )
    if not out and "ani-grid" not in html and "ничего не найдено" not in html.lower():
        raise LayoutChanged("поиск", "блок .ani-grid__item")
    return out


def parse_title_page(html: str, anime_id: int, url: str) -> TitleInfo:
    soup = parse_html(html)
    ld: dict[str, Any] | None = None
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(s.text(strip=False))
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("@type") in ("TVSeries", "Movie", "CreativeWork"):
            ld = obj
            break
    h1 = soup.select_one("h1")
    if not ld and not h1:
        raise LayoutChanged("карточка", "JSON-LD и <h1>")
    ld = ld or {}
    rating = ld.get("aggregateRating") or {}
    company = ld.get("productionCompany")
    if isinstance(company, list):
        company = company[0] if company else None
    genres = ld.get("genre") or []
    if isinstance(genres, str):
        genres = [genres]
    return TitleInfo(
        anime_id=anime_id,
        url=url,
        title=ld.get("name") or (h1.text() if h1 else ""),
        kind={"TVSeries": "series", "Movie": "movie"}.get(ld.get("@type") or "", ld.get("@type")),
        alternate_name=ld.get("alternateName"),
        description=ld.get("description"),
        poster=ld.get("image"),
        genres=list(genres),
        date_published=ld.get("datePublished"),
        episodes_total=ld.get("numberOfEpisodes"),
        rating=rating.get("ratingValue"),
        studio=company.get("name") if isinstance(company, dict) else None,
    )


def parse_player_episodes(root: Node) -> tuple[list[EpisodeInfo], list[int]]:
    """Episodes in the player HTML and the page numbers (episodes come in hundreds)."""
    eps: list[EpisodeInfo] = []
    for el in root.select("[data-episode-number][data-episode]"):
        try:
            eps.append(EpisodeInfo(number=int(el["data-episode-number"]), episode_id=int(el["data-episode"])))
        except ValueError:
            continue
    pages = [0]
    holder = root.select_one("[data-anime-player-episodes-pages-value]")
    if holder:
        try:
            pages = [p["page"] for p in json.loads(holder["data-anime-player-episodes-pages-value"])]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return eps, pages or [0]


def parse_providers(root: Node) -> list[PlayerOption]:
    return [
        PlayerOption(
            provider=b["data-provider-slug"],
            provider_title=b.get("data-provider-title") or b["data-provider-slug"],
            translation_id=b.get("data-translation-id") or b.get("data-ptranslation") or "",
            translation=b.get("data-translation-title") or "",
            embed_url=_abs(b["data-player"]),
        )
        for b in root.select("[data-provider-slug][data-player]")
    ]


def parse_schedule(html: str) -> dict[int, tuple[str | None, str | None]]:
    """Schedule table. A row is 4 cells in a row:
    [data-label="N."] «N серия» · name · [data-episode][data-number] with the date · marks."""
    result: dict[int, tuple[str | None, str | None]] = {}
    for cell in parse_html(html).select("[data-episode][data-number]"):
        try:
            number = int(cell["data-number"])
        except ValueError:
            continue
        date_el = cell.select_one("[data-label]")
        date = date_el.text(" ") if date_el else None
        title = None
        prev = cell.previous_element()
        if prev is not None and not prev.has_attr("data-label"):
            title = prev.text(" ") or None
        result[number] = (title, date or None)
    return result


def parse_schedule_template(html: str) -> str | None:
    el = parse_html(html).select_one(".schedule-episodes-table[data-infinite-scroll-url-template-value]")
    return el["data-infinite-scroll-url-template-value"] if el else None


# ---- players → streams


class Resolver:
    def __init__(self, http: Http, base_url: str = DEFAULT_BASE_URL) -> None:
        self.http = http
        self.base = base_url.rstrip("/")
        self.referer = self.base + "/"

    def resolve(self, opt: PlayerOption) -> list[RawStream]:
        fn = {"cvh": self.cvh, "kodik": self.kodik, "aniboom": self.aniboom}.get(opt.provider)
        if not fn:
            raise UnsupportedPlayer(f"плеер {opt.provider_title} пока не поддерживается")
        streams = fn(opt)
        streams.sort(key=lambda s: ({"mp4": 0, "hls": 1, "dash": 2}.get(s.kind, 3), -(s.quality or 0)))
        return streams

    # CVH (cdnvideohub): iframe on animego → public JSON API → direct mp4 on okcdn
    def cvh(self, opt: PlayerOption) -> list[RawStream]:
        path = urlparse(opt.embed_url).path  # /cdn-iframe/{titleId}/{voice}/{season}/{episode}
        parts = [unquote(p) for p in path.split("/") if p]
        if len(parts) < 5 or parts[0] != "cdn-iframe":
            raise LayoutChanged("cvh", "ссылка /cdn-iframe/{id}/{озвучка}/{сезон}/{серия}")
        title_id, voice, season, episode = parts[1], parts[2], int(parts[3]), int(parts[4])
        pub, aggr = "747", "mali"
        try:
            vp = parse_html(self.http.get(opt.embed_url, headers={"Referer": self.referer}, cache=True)).select_one(
                "video-player"
            )
            if vp:
                pub = vp.get("data-publisher-id") or pub
                aggr = vp.get("data-aggregator") or aggr
        except AnimeGoError:
            pass  # defaults taken from the live site on 2026-10-25
        headers = {"Referer": self.referer, "Origin": self.base}
        playlist = self.http.get_json(f"{CVH_API}/playlist?pub={pub}&aggr={aggr}&id={title_id}&ep={episode}", headers=headers)
        item = pick_cvh_item(playlist.get("items") or [], voice, season, episode)
        if not item:
            raise NotFound(f"cvh: нет озвучки {voice} для {season}x{episode}")
        video = self.http.get_json(f"{CVH_API}/video/{item['vkId']}", headers=headers)
        return cvh_streams(video, opt.translation or voice)

    # Kodik: player page (with animego Referer) → signed params → POST /ftor → ROT18 + base64
    def kodik(self, opt: PlayerOption) -> list[RawStream]:
        page_url = opt.embed_url
        html = self.http.get(page_url, headers={"Referer": self.referer})
        params = parse_kodik_page(html)
        origin = "{0.scheme}://{0.netloc}".format(urlparse(page_url))
        endpoint = self._kodik_endpoint(html, origin)
        signed = {k: params["url_params"][k] for k in KODIK_SIGNED_KEYS if k in params["url_params"]}
        if "ref" in signed:  # urlParams keeps it percent-encoded; /ftor answers 500 unless it gets the plain URL
            signed["ref"] = unquote(signed["ref"])
        if signed.get("d") != urlparse(self.base).hostname:
            raise Blocked(f"kodik: подпись выдана для {signed.get('d')!r}, а не для animego")
        body = {
            **signed, "type": params["type"], "hash": params["hash"], "id": params["id"],
            "bad_user": "false", "cdn_is_working": "true", "info": "{}",
        }  # fmt: skip
        text = self.http.post(
            origin + endpoint,
            data=body,
            headers={"X-Requested-With": "XMLHttpRequest", "Referer": page_url, "Origin": origin},
        )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LayoutChanged("kodik", f"JSON от {endpoint} (подпись не принята?)") from e
        return kodik_streams(data, opt.translation)

    def _kodik_endpoint(self, html: str, origin: str) -> str:
        """The endpoint is baked into the player JS as atob("...") next to type:"POST"."""
        m = re.search(r'<script[^>]+src="(/assets/js/app\.player[^"]+\.js)"', html)
        if not m:
            return KODIK_FALLBACK_ENDPOINT
        try:
            js = self.http.get(origin + m.group(1), cache=True)
        except AnimeGoError:
            return KODIK_FALLBACK_ENDPOINT
        found = re.search(r'type:\s*"POST",\s*url:\s*atob\("([A-Za-z0-9+/=]+)"\)', js)
        if not found:
            return KODIK_FALLBACK_ENDPOINT
        return base64.b64decode(found.group(1)).decode()

    # Aniboom: embed (with animego Referer) → data-parameters → HLS/DASH with fMP4 segments
    def aniboom(self, opt: PlayerOption) -> list[RawStream]:
        return aniboom_streams(self.http.get(opt.embed_url, headers={"Referer": self.referer}), opt.translation)


def pick_cvh_item(items: list[dict], voice: str, season: int, episode: int) -> dict | None:
    same_ep = [i for i in items if i.get("episode") == episode and i.get("season", season) == season]
    norm = voice.casefold().strip()
    for key in ("voiceStudio", "voiceType"):
        for i in same_ep:
            if (i.get(key) or "").casefold().strip() == norm:
                return i
    return None


def cvh_streams(video: dict, translation: str) -> list[RawStream]:
    src = video.get("sources")
    if not isinstance(src, dict):
        raise LayoutChanged("cvh", "sources в ответе /video")
    out = [RawStream("cvh", translation, "mp4", q, src[k]) for k, q in CVH_QUALITIES.items() if src.get(k)]
    if src.get("hlsUrl"):
        out.append(RawStream("cvh", translation, "hls", None, src["hlsUrl"]))
    if src.get("dashUrl"):
        out.append(RawStream("cvh", translation, "dash", None, src["dashUrl"]))
    return out


def parse_kodik_page(html: str) -> dict:
    m = re.search(r"urlParams\s*=\s*'(\{.*?\})'", html)
    if not m:
        raise LayoutChanged("kodik", "urlParams на странице плеера")
    info = {}
    for key in ("type", "hash", "id"):
        mm = re.search(r"vInfo\." + key + r"\s*=\s*'([^']+)'", html)
        if not mm:
            raise LayoutChanged("kodik", f"vInfo.{key}")
        info[key] = mm.group(1)
    return {"url_params": json.loads(m.group(1)), **info}


def kodik_decode(src: str) -> str:
    """Every Latin letter is shifted by +18 around the alphabet, then base64."""
    if "//" in src:
        return src

    def shift(ch: str) -> str:
        limit = 90 if ch <= "Z" else 122
        code = ord(ch) + 18
        return chr(code if code <= limit else code - 26)

    shifted = re.sub(r"[A-Za-z]", lambda m: shift(m.group(0)), src)
    shifted += "=" * (-len(shifted) % 4)
    return base64.b64decode(shifted).decode()


def kodik_streams(data: dict, translation: str) -> list[RawStream]:
    links = data.get("links")
    if not isinstance(links, dict) or not links:
        raise NotFound("kodik: в ответе нет ссылок")
    headers = {"Referer": "https://kodikplayer.com/"}
    out = []
    for q, arr in links.items():
        quality = int(q) if q.isdigit() else None
        for entry in arr:
            url = _abs(kodik_decode(entry["src"]))
            out.append(RawStream("kodik", translation, "hls", quality, url, headers))
            if url.endswith(":hls:manifest.m3u8"):  # cutting the suffix leaves a direct mp4
                out.append(RawStream("kodik", translation, "mp4", quality, url[: -len(":hls:manifest.m3u8")], headers))
    return out


def aniboom_streams(html: str, translation: str) -> list[RawStream]:
    video = parse_html(html).select_one("#video[data-parameters]")
    if not video:
        raise LayoutChanged("aniboom", "#video[data-parameters]")
    params = json.loads(video["data-parameters"])
    headers = {"Referer": "https://aniboom.one/", "Origin": "https://aniboom.one"}
    out = []
    for kind in ("hls", "dash"):
        raw = params.get(kind)
        if not raw or raw == "null":
            continue
        try:
            src = json.loads(raw)["src"] if isinstance(raw, str) else raw["src"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        out.append(RawStream("aniboom", translation, kind, params.get("qualityVideo"), src, headers))
    if not out:
        raise NotFound("aniboom: в data-parameters нет hls/dash")
    return out


def rank_options(options: list[PlayerOption]) -> list[PlayerOption]:
    rank = {p: i for i, p in enumerate(PROVIDER_PRIORITY)}
    return sorted(options, key=lambda o: rank.get(o.provider, 99))
