"""
A script to display the `MODULE LEVEL` magic variables.

This shows how to use the **CONFIGPATH** and **LOGGING_CONFIG** magic
variables to provide sensible defaults to a script.
"""

import argparse
import asyncio
import logging

import luxos.cli.v1 as cli

log = logging.getLogger(__name__)

CONFIGPATH = "booo.yaml"  # this will override the default config.yaml

# You can override the default values here
# (LOGGING_CONFIG will be passed to logging.basicConfig(**LOGGING_CONFIG))
# In this case the script will be very quiet by default (you'd need to pass few `-v`
# flags to display the log messages.
LOGGING_CONFIG = {
    "level": logging.WARNING,
    "format": "%(asctime)s [%(levelname)s] %(message)s",
    "handlers": [logging.StreamHandler(), logging.FileHandler("LuxOS-LoadControl.log")],
}


@cli.cli()
async def main(args: argparse.Namespace):
    # show some logging info
    log.debug("a debug message, need to use -v|--verbose to display it")
    log.info("an info message, you can silence it with -q|--quiet")
    log.warning("a warning!")
    print(f"The config file is: {args.config=}")


if __name__ == "__main__":
    asyncio.run(main())
