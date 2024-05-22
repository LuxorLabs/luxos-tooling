import argparse
import asyncio
import logging

import luxos.cli.v1 as cli

log = logging.getLogger(__name__)

CONFIGPATH = "booo.yaml"
LOGGING_CONFIG = {
    "level": logging.WARNING,
    "format": "%(asctime)s [%(levelname)s] %(message)s",
    "handlers": [logging.StreamHandler(), logging.FileHandler("LuxOS-LoadControl.log")],
}


@cli.cli()
async def main(args: argparse.Namespace):
    log.debug("a debug message")
    log.info("an info message")
    log.warning("a warning!")
    print(f"Got: {args.config=}")


if __name__ == "__main__":
    asyncio.run(main())
