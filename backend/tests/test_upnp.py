import asyncio
import xml.etree.ElementTree as ET
from functools import partial

import httpx

from easytv.core.models import PlaybackState
from easytv.infrastructure.upnp import UpnpTvController

from test_scenarios import LIVING_ROOM


def test_tv_seek_uses_track_time_and_reads_zero_position(monkeypatch):
    actions = []

    def soap(request: httpx.Request) -> httpx.Response:
        action = request.headers["SOAPAction"].strip('"').split("#")[-1]
        actions.append(action)
        if action == "GetTransportInfo":
            return httpx.Response(200, text="<CurrentTransportState>PAUSED_PLAYBACK</CurrentTransportState>")
        if action == "GetPositionInfo":
            return httpx.Response(200, text="<RelTime>00:00:00.000</RelTime><TrackDuration>00:00:00</TrackDuration>")

        assert action == "Seek"
        body = ET.fromstring(request.content)
        seek = body.find(f".//{{{LIVING_ROOM.service_type}}}Seek")
        assert seek is not None
        assert {arg.tag: arg.text for arg in seek} == {
            "InstanceID": "0",
            "Unit": "REL_TIME",
            "Target": "01:02:03",
        }
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(soap)))
    controller = UpnpTvController()

    async def scenario():
        await controller.seek(LIVING_ROOM, 3723)
        return await controller.info(LIVING_ROOM)

    info = asyncio.run(scenario())
    assert (info.state, info.position_s, info.duration_s) == (PlaybackState.PAUSED, 0, None)
    assert actions == ["Seek", "GetTransportInfo", "GetPositionInfo"]
