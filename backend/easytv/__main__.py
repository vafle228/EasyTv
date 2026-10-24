import logging

import uvicorn

from easytv.api.app import create_app
from easytv.config import Settings
from easytv.container import build_container


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per TV request every few seconds is noise
    settings = Settings.from_env()
    app = create_app(build_container(settings))
    log = logging.getLogger("easytv")
    log.info("EasyTv on http://%s:%d", settings.public_host or "localhost", settings.port)
    log.info(
        "TV discovery: SSDP every %ss; known addresses=%s; subnets=%s",
        settings.discovery_interval_s,
        settings.seeds or "none",
        settings.scan_subnets or "none",
    )
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
