"""DLNA/UPnP adapters: TV discovery (SSDP + device description) and AVTransport control (SOAP)."""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import re
import socket
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit
from xml.sax.saxutils import escape

import httpx

from easytv.core.errors import TvCommandError
from easytv.core.models import MediaItem, PlaybackInfo, PlaybackState, Tv

from . import ssdp

log = logging.getLogger(__name__)

DLNA_FLAGS = "DLNA.ORG_OP=01;DLNA.ORG_CI=0;DLNA.ORG_FLAGS=01700000000000000000000000000000"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if _local(child.tag) == name:
            return (child.text or "").strip() or None
    return None


def parse_renderer(xml_text: str, location: str, ip: str) -> Tv | None:
    """Build a Tv from a UPnP device description, or None if the device can't play media (no AVTransport)."""
    try:
        root = ET.fromstring(xml_text.lstrip("﻿").encode("utf-8"))
    except ET.ParseError:
        return None

    base = location
    for el in root.iter():
        if _local(el.tag) == "URLBase" and (el.text or "").strip():
            base = el.text.strip()
            break

    for device in (el for el in root.iter() if _local(el.tag) == "device"):
        services = next((el for el in device if _local(el.tag) == "serviceList"), None)
        if services is None:
            continue
        for service in services:
            service_type = _find_text(service, "serviceType") or ""
            control = _find_text(service, "controlURL")
            if ":AVTransport:" in service_type and control:
                udn = _find_text(device, "UDN") or ip
                return Tv(
                    id=re.sub(r"[^A-Za-z0-9_-]", "-", udn.removeprefix("uuid:")),
                    name=_find_text(device, "friendlyName") or ip,
                    ip=ip,
                    control_url=urljoin(base, control),
                    service_type=service_type,
                    manufacturer=_find_text(device, "manufacturer"),
                    model=_find_text(device, "modelName"),
                    location=location,
                )
    return None


class SsdpTvDiscovery:
    """TvDiscovery port: SSDP search, then read each device description."""

    def __init__(self, unicast_hosts: list[str], scan_subnets: list[str], timeout: float = 3.0) -> None:
        ips = [h for h in unicast_hosts if _is_ip(h)]
        self._hosts = list(dict.fromkeys(ips + ssdp.sweep_hosts(scan_subnets)))
        self._timeout = timeout

    async def discover(self) -> list[Tv]:
        responses = await asyncio.to_thread(ssdp.search, ssdp.RENDERER_TARGETS, self._hosts, self._timeout)
        locations = {(r.ip, r.location) for r in responses}
        log.debug("SSDP: %d answer(s) from %s", len(responses), sorted({r.ip for r in responses}))
        async with httpx.AsyncClient(timeout=4.0, trust_env=False) as client:
            results = await asyncio.gather(*(self._describe(client, ip, loc) for ip, loc in locations))
        tvs: dict[str, Tv] = {}
        for tv in results:
            if tv is not None:
                tvs.setdefault(tv.id, tv)
        return list(tvs.values())

    @staticmethod
    async def _describe(client: httpx.AsyncClient, ip: str, location: str) -> Tv | None:
        try:
            resp = await client.get(location)
            resp.raise_for_status()
            return parse_renderer(resp.text, location, ip)
        except (httpx.HTTPError, ValueError) as exc:
            log.debug("Cannot read description %s: %s", location, exc)
            return None


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


# Where TVs usually publish their DLNA renderer description. Used when we only know the IP
# and SSDP can't reach the TV (Docker) or the TV ignores unicast search (UPnP 1.0 devices).
WELL_KNOWN_DESCRIPTIONS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (9197, ("/dmr",)),  # Samsung Tizen, 2016+
    (7676, tuple(f"/smp_{n}_" for n in range(1, 31))),  # Samsung 2013-2015 (AllShare)
    (52235, ("/dmr/SamsungMRDesc.xml", "/MediaRenderer/desc.xml")),  # Samsung 2010-2012
    (49152, ("/description.xml", "/rootDesc.xml", "/dmr.xml", "/upnp/dev/desc.xml")),  # libupnp-based TVs
    (8008, ("/ssdp/device-desc.xml",)),  # Chromecast / Android TV
)


class UpnpTvLocator:
    """TvLocator port: reads device descriptions over plain HTTP (works through Docker NAT)."""

    def __init__(self, timeout: float = 3.0) -> None:
        self._timeout = timeout

    async def describe(self, location: str) -> Tv | None:
        host = urlsplit(location).hostname
        if not host:
            return None
        async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
            return await SsdpTvDiscovery._describe(client, host, location)

    async def locate(self, address: str) -> Tv | None:
        address = address.strip()
        if address.startswith(("http://", "https://")):
            return await self.describe(address)
        host = address.split(":", 1)[0]
        if not _is_ip(host):
            try:
                host = await asyncio.to_thread(socket.gethostbyname, host)
            except OSError:
                return None

        # 1. Ask the TV directly over SSDP (UPnP 1.1 devices answer a unicast search).
        responses = await asyncio.to_thread(ssdp.search, ssdp.RENDERER_TARGETS, [host], 1.5)
        for resp in responses:
            if resp.ip == host and (tv := await self.describe(resp.location)):
                return tv

        # 2. Try the well-known description URLs on the ports that are open.
        async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
            for port, paths in WELL_KNOWN_DESCRIPTIONS:
                if not await _port_open(host, port):
                    continue
                for path in paths:
                    tv = await SsdpTvDiscovery._describe(client, host, f"http://{host}:{port}{path}")
                    if tv:
                        log.info("Found %s at http://%s:%d%s", tv.name, host, port, path)
                        return tv
        log.info("No DLNA renderer found at %s", address)
        return None


async def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, asyncio.TimeoutError):
        return False
    writer.close()
    with contextlib.suppress(Exception):
        await writer.wait_closed()
    return True


def didl_metadata(media: MediaItem) -> str:
    flags = DLNA_FLAGS if media.url.startswith("http://") else "*"
    return (
        '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" '
        'xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/">'
        '<item id="0" parentID="-1" restricted="1">'
        f"<dc:title>{escape(media.title)}</dc:title>"
        "<upnp:class>object.item.videoItem</upnp:class>"
        f'<res protocolInfo="http-get:*:{media.mime}:{flags}">{escape(media.url)}</res>'
        "</item></DIDL-Lite>"
    )


_STATE_MAP = {
    "PLAYING": PlaybackState.PLAYING,
    "PAUSED_PLAYBACK": PlaybackState.PAUSED,
    "STOPPED": PlaybackState.STOPPED,
    "TRANSITIONING": PlaybackState.TRANSITIONING,
    "NO_MEDIA_PRESENT": PlaybackState.NO_MEDIA,
}


def _parse_time(value: str | None) -> int | None:
    if not value or value.upper() == "NOT_IMPLEMENTED":
        return None
    match = re.match(r"^(\d+):(\d{1,2}):(\d{1,2})", value)
    if not match:
        return None
    h, m, s = (int(x) for x in match.groups())
    total = h * 3600 + m * 60 + s
    return total or None


def _xml_value(xml_text: str, name: str) -> str | None:
    match = re.search(rf"<(?:\w+:)?{name}>([^<]*)</(?:\w+:)?{name}>", xml_text)
    return match.group(1).strip() if match else None


class UpnpTvController:
    """TvController port over UPnP AVTransport SOAP calls."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    async def play(self, tv: Tv, media: MediaItem) -> None:
        try:
            await self._call(tv, "Stop")
        except TvCommandError:
            pass  # the TV may already be idle
        await asyncio.sleep(0.5)
        await self._call(
            tv,
            "SetAVTransportURI",
            f"<CurrentURI>{escape(media.url)}</CurrentURI>"
            f"<CurrentURIMetaData>{escape(didl_metadata(media))}</CurrentURIMetaData>",
        )
        await asyncio.sleep(0.5)
        await self._call(tv, "Play", "<Speed>1</Speed>")

    async def pause(self, tv: Tv) -> None:
        await self._call(tv, "Pause")

    async def resume(self, tv: Tv) -> None:
        await self._call(tv, "Play", "<Speed>1</Speed>")

    async def stop(self, tv: Tv) -> None:
        await self._call(tv, "Stop")

    async def info(self, tv: Tv) -> PlaybackInfo:
        try:
            transport = await self._call(tv, "GetTransportInfo")
        except TvCommandError:
            return PlaybackInfo(state=PlaybackState.UNKNOWN)
        state = _STATE_MAP.get((_xml_value(transport, "CurrentTransportState") or "").upper(), PlaybackState.UNKNOWN)
        position = duration = None
        if state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            try:
                pos = await self._call(tv, "GetPositionInfo")
                position = _parse_time(_xml_value(pos, "RelTime"))
                duration = _parse_time(_xml_value(pos, "TrackDuration"))
            except TvCommandError:
                pass
        return PlaybackInfo(state=state, position_s=position, duration_s=duration)

    async def _call(self, tv: Tv, action: str, args: str = "") -> str:
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<s:Body><u:{action} xmlns:u="{tv.service_type}">'
            f"<InstanceID>0</InstanceID>{args}</u:{action}></s:Body></s:Envelope>"
        )
        headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPACTION": f'"{tv.service_type}#{action}"',
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
                resp = await client.post(tv.control_url, content=body.encode("utf-8"), headers=headers)
        except httpx.HTTPError as exc:
            raise TvCommandError(f"Телевизор {tv.name} не отвечает ({action}): {exc}") from exc
        if resp.status_code >= 400:
            code = _xml_value(resp.text, "errorCode")
            desc = _xml_value(resp.text, "errorDescription")
            detail = f"UPnP ошибка {code} {desc or ''}".strip() if code else f"HTTP {resp.status_code}"
            raise TvCommandError(f"Телевизор {tv.name} отклонил команду {action}: {detail}")
        return resp.text
