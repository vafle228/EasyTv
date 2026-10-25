"""The animego adapter on pages saved from the live site (2026-10-25). No network: URLs map to fixture files."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from easytv.core.errors import CatalogItemNotFound
from easytv.core.models import StreamRef, TitleKind
from easytv.infrastructure.animego import AnimegoCatalog
from easytv.infrastructure.animego import client as ag
from easytv.infrastructure.animego.dom import parse_html

FX = Path(__file__).parent / "fixtures" / "animego"
FRIREN = "provozhayuschaya-v-posledniy-put-friren-2430"

ROUTES = [
    (r"/search/all\?q=", "search_friren.html"),
    (rf"/anime/{FRIREN}$", "title_2430.html"),
    (r"/anime/2430/26/schedule/load/1$", "schedule_2430_p1.json"),
    (r"/player/2430$", "player_2430.json"),
    (r"/player/videos/31684$", "player_videos_31684.json"),
    (r"/player/385$", "player_385.json"),
    (r"/player/103$", "player_103.json"),
    (r"/player/103/episodes\?page=\d$", "player_103_episodes_p3.json"),
    (r"/cdn-iframe/52991/", "cvh_iframe.html"),
    (r"plapi\.cdnvideohub\.com/.*/playlist\?pub=747&aggr=mali&id=52991&ep=2$", "cvh_playlist_52991.json"),
    (r"plapi\.cdnvideohub\.com/.*/video/7584549198442$", "cvh_video.json"),
    (r"aniboom\.one/embed/", "aniboom_embed.html"),
    (r"kodikplayer\.com/seria/", "kodik_seria.html"),
    (r"kodikplayer\.com/assets/js/app\.player", "kodik_app.js"),
    (r"kodikplayer\.com/ftor$", "kodik_ftor.json"),
]


class FakeHttp(ag.Http):
    def __init__(self) -> None:
        super().__init__(delay=0)
        self.calls: list[tuple[str, str, dict]] = []
        self.broken: set[str] = set()  # fixture names that answer 404

    def request(self, method, url, *, cache=False, **kw):
        self.calls.append((method, url, kw))
        for pattern, name in ROUTES:
            if re.search(pattern, url):
                if name in self.broken:
                    raise ag.NotFound(f"404: {url}")
                return (FX / name).read_text(encoding="utf-8")
        raise ag.NotFound(f"404: {url}")


@pytest.fixture
def site():
    http = FakeHttp()
    return AnimegoCatalog(http), http


def test_search_keeps_only_anime(site):
    catalog, _ = site
    res = catalog.search("фрирен")
    assert [r.id for r in res] == [FRIREN, "provozhayuschaya-v-posledniy-put-friren-2-2911"]
    first = res[0]
    assert (first.original_title, first.kind, first.year, first.rating) == ("Sousou no Frieren", "Сериал", "2023", "9.4")
    assert first.poster and first.poster.startswith("https://img.cdngos.com/")


def test_title_card_from_json_ld(site):
    catalog, _ = site
    t = catalog.title(FRIREN)
    assert (t.kind, t.episodes_total, t.studio, t.year, t.rating) == (TitleKind.SERIES, 28, "Madhouse", "2023", 9.4)
    assert "Фэнтези" in t.genres and t.original_title == "Frieren: Beyond Journey's End"


def test_episodes_with_schedule_titles(site):
    catalog, _ = site
    eps = {e.number: e for e in catalog.episodes(FRIREN)}
    assert sorted(eps) == [1, 2, 3]  # the player fixture has 3 episodes; schedule names start at 24
    assert eps[2].title is None


def test_schedule_parser():
    page = (FX / "title_2430.html").read_text(encoding="utf-8")
    assert ag.parse_schedule(page)[28] == ("It Would Be Embarrassing When We Met Again", "22 марта 2024")
    p1 = json.loads((FX / "schedule_2430_p1.json").read_text(encoding="utf-8"))
    assert ag.parse_schedule(p1["data"]["content"])[24] == ("Perfect Replicas", "23 февраля 2024")
    assert ag.parse_schedule_template(page) == "/anime/2430/26/schedule/load/__page__"


def test_long_series_is_paginated(site):
    catalog, http = site
    numbers = [e.number for e in catalog.episodes("naruto-uragannye-hroniki-103")]
    assert 301 in numbers
    assert sum("/player/103/episodes?page=" in c[1] for c in http.calls) == 4


def test_dubs_of_an_episode_group_players_in_priority_order(site):
    catalog, http = site
    variants = catalog.variants(FRIREN, 2)
    assert [(v.translation, v.providers) for v in variants] == [
        ("Dream Cast", ("cvh", "kodik", "aniboom")),
        ("AniLibria", ("cvh", "kodik", "aniboom")),
        ("Студийная Банда", ("cvh",)),
    ]
    assert any(c[1].endswith("/player/videos/31684") for c in http.calls)
    xhr = [c for c in http.calls if "/player/" in c[1]]
    assert all(c[2]["headers"]["X-Requested-With"] == "XMLHttpRequest" for c in xhr)


def test_movie_has_players_without_episodes(site):
    catalog, _ = site
    assert catalog.episodes("boruto-film-naruto-385") == []
    assert [v.translation for v in catalog.variants("boruto-film-naruto-385", 0)] == ["AniLibria", "AniDUB"]


def test_cvh_gives_direct_mp4_first(site):
    catalog, http = site
    streams = catalog.streams(StreamRef(FRIREN, 2, "81"))
    assert (streams[0].provider, streams[0].kind, streams[0].quality) == ("cvh", "mp4", 1080)
    assert "okcdn.ru" in streams[0].url
    assert any("ep=2" in c[1] for c in http.calls if "/playlist?" in c[1])


def test_kodik_direct_mp4_and_signed_request(site):
    catalog, http = site
    streams = catalog.streams(StreamRef(FRIREN, 2, "81", provider="kodik"))
    mp4 = [s for s in streams if s.kind == "mp4"]
    assert mp4[0].quality == 720 and mp4[0].url.startswith("https://") and mp4[0].url.endswith("/720.mp4")
    post = next(c for c in http.calls if c[0] == "POST")
    assert set(post[2]["data"]) - {"type", "hash", "id", "bad_user", "cdn_is_working", "info"} == set(ag.KODIK_SIGNED_KEYS)
    assert post[2]["data"]["d"] == "animego.me"
    page = next(c for c in http.calls if "/seria/" in c[1])
    assert page[2]["headers"]["Referer"] == "https://animego.me/"


def test_auto_falls_back_to_next_player(site):
    catalog, http = site
    http.broken.add("cvh_playlist_52991.json")
    streams = catalog.streams(StreamRef(FRIREN, 2, "81"))
    assert streams[0].provider == "kodik" and streams[0].kind == "mp4"


def test_aniboom_is_hls_only(site):
    catalog, _ = site
    streams = catalog.streams(StreamRef(FRIREN, 2, "81", provider="aniboom"))
    assert [s.kind for s in streams] == ["hls", "dash"]
    assert streams[0].headers["Referer"] == "https://aniboom.one/"


def test_unknown_dub_is_not_found(site):
    catalog, _ = site
    with pytest.raises(CatalogItemNotFound):
        catalog.streams(StreamRef(FRIREN, 2, "999"))


def test_kodik_decode():
    data = json.loads((FX / "kodik_ftor.json").read_text())
    url = ag.kodik_decode(data["links"]["720"][0]["src"])
    assert re.match(r"^//[\w.-]+/useruploads/[0-9a-f-]+/[0-9a-f]+:\d{10}/720\.mp4:hls:manifest\.m3u8$", url)


def test_layout_change_is_reported():
    with pytest.raises(ag.LayoutChanged):
        ag.parse_kodik_page("<html>новая вёрстка</html>")
    with pytest.raises(ag.LayoutChanged):
        ag.aniboom_streams("<html></html>", "x")
    with pytest.raises(ag.LayoutChanged):
        ag.parse_search("<html><body>другая страница</body></html>", "https://animego.me")


def test_dom_selectors():
    root = parse_html('<div class="a b"><p id="x" data-k="1">hi <b>there</b></p><img src="i.png"><p data-k="2">x</p></div>')
    assert [p["data-k"] for p in root.select("div.a p[data-k]")] == ["1", "2"]
    assert root.select_one("#x").text(" ") == "hi there"
    assert root.select_one('p[data-k="2"]').previous_element().tag == "img"
    assert root.select("span") == []
