"""Finds DLNA media renderers (TVs) from the host and prints their description URLs, one per line.

Used by run.sh on macOS/Linux (Windows uses discover.ps1). Standard library only.
"""

import re
import select
import socket
import sys
import time

TARGETS = ("urn:schemas-upnp-org:device:MediaRenderer:1", "urn:schemas-upnp-org:service:AVTransport:1")


def main(seconds: float = 4.0) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.setblocking(False)
    for st in TARGETS:
        msg = f'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 2\r\nST: {st}\r\n\r\n'
        for _ in range(2):
            try:
                sock.sendto(msg.encode(), ("239.255.255.250", 1900))
            except OSError:
                pass
    found: set[str] = set()
    deadline = time.monotonic() + seconds
    while (left := deadline - time.monotonic()) > 0:
        if select.select([sock], [], [], min(left, 0.25))[0]:
            try:
                data, _ = sock.recvfrom(65507)
            except OSError:
                continue
            if m := re.search(r"(?im)^LOCATION:\s*(\S+)", data.decode("utf-8", "replace")):
                found.add(m.group(1))
    print("\n".join(sorted(found)))


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 4.0)
