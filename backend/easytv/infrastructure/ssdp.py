"""SSDP search: multicast on every local interface plus unicast probes.

Multicast is how DLNA discovery normally works, but it does not leave a Docker bridge
network (and Docker Desktop on Windows/macOS). So we also send unicast M-SEARCH packets
directly to configured hosts and to every address of the configured subnets; UPnP 1.1
devices answer those too, and the answers come back through NAT.
"""

from __future__ import annotations

import ipaddress
import logging
import select
import socket
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
MAX_SWEEP_HOSTS = 1024

RENDERER_TARGETS = (
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "urn:schemas-upnp-org:service:AVTransport:1",
)


@dataclass(frozen=True)
class SsdpResponse:
    ip: str
    location: str
    st: str
    server: str | None
    usn: str | None


def _msearch(st: str, host: str = f"{SSDP_ADDR}:{SSDP_PORT}", mx: int = 2) -> bytes:
    return (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {host}\r\n"
        'MAN: "ssdp:discover"\r\n'
        f"MX: {mx}\r\n"
        f"ST: {st}\r\n"
        "\r\n"
    ).encode("ascii")


def parse_response(data: bytes, ip: str) -> SsdpResponse | None:
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:
        return None
    lines = text.split("\r\n") if "\r\n" in text else text.split("\n")
    if not lines or not lines[0].upper().startswith("HTTP/"):
        return None
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().upper()] = value.strip()
    location = headers.get("LOCATION")
    if not location:
        return None
    return SsdpResponse(
        ip=ip,
        location=location,
        st=headers.get("ST", ""),
        server=headers.get("SERVER"),
        usn=headers.get("USN"),
    )


def local_ipv4_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addresses.add(str(info[4][0]))
    except OSError:
        pass
    # The address used for the default route (works even when hostname resolution is poor).
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            addresses.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(a for a in addresses if not a.startswith(("127.", "169.254.")))


def sweep_hosts(subnets: list[str]) -> list[str]:
    hosts: list[str] = []
    for subnet in subnets:
        try:
            net = ipaddress.ip_network(subnet, strict=False)
        except ValueError:
            log.warning("Ignoring invalid subnet %r", subnet)
            continue
        if net.num_addresses > MAX_SWEEP_HOSTS + 2:
            log.warning("Subnet %s is too large to sweep (max /22), skipping", subnet)
            continue
        hosts.extend(str(h) for h in net.hosts())
    return hosts


def search(
    targets: tuple[str, ...] = RENDERER_TARGETS,
    unicast_hosts: list[str] | None = None,
    timeout: float = 3.0,
) -> list[SsdpResponse]:
    """Blocking SSDP search. Returns unique (ip, location) responses."""
    sockets: list[socket.socket] = []
    for local_ip in local_ipv4_addresses() or ["0.0.0.0"]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setblocking(False)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.bind((local_ip, 0))
            if local_ip != "0.0.0.0":
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_ip))
            sockets.append(sock)
        except OSError as exc:
            log.debug("Cannot use interface %s for SSDP: %s", local_ip, exc)

    if not sockets:
        return []

    try:
        for sock in sockets:
            for st in targets:
                for _ in range(2):
                    try:
                        sock.sendto(_msearch(st), (SSDP_ADDR, SSDP_PORT))
                    except OSError:
                        pass
        # Unicast probes go out through one socket: the OS picks the right interface by route.
        if unicast_hosts:
            sender = sockets[0] if len(sockets) == 1 else _default_route_socket(sockets)
            for host in unicast_hosts:
                for st in targets:
                    try:
                        sender.sendto(_msearch(st, host=f"{host}:{SSDP_PORT}", mx=1), (host, SSDP_PORT))
                    except OSError:
                        pass

        found: dict[tuple[str, str], SsdpResponse] = {}
        deadline = time.monotonic() + timeout
        while (remaining := deadline - time.monotonic()) > 0:
            readable, _, _ = select.select(sockets, [], [], min(remaining, 0.25))
            for sock in readable:
                while True:
                    try:
                        data, (ip, _port) = sock.recvfrom(65507)
                    except (BlockingIOError, OSError):
                        break
                    resp = parse_response(data, ip)
                    if resp and (resp.ip, resp.location) not in found:
                        found[(resp.ip, resp.location)] = resp
        return list(found.values())
    finally:
        for sock in sockets:
            sock.close()


def _default_route_socket(sockets: list[socket.socket]) -> socket.socket:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            default_ip = probe.getsockname()[0]
        for sock in sockets:
            if sock.getsockname()[0] == default_ip:
                return sock
    except OSError:
        pass
    return sockets[0]
