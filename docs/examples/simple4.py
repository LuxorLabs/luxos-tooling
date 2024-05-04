import argparse
import asyncio
import logging

import luxos.cli.v1 as cli
from luxos import utils

log = logging.getLogger(__name__)

CONFIGPATH = "miners.csv"


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-b",
        "--batch",
        type=int,
        help="execute command limiting to batch concurrent operations",
    )
    parser.add_argument("-p", "--port", type=int, default=4028)
    parser.add_argument("command")
    parser.add_argument("extra", nargs="*")


@cli.cli(add_arguments)
async def main(args: argparse.Namespace):
    addresses = utils.load_ips_from_csv(args.config, port=args.port)
    for result in await utils.launch(
        addresses, utils.rexec, args.command, args.extra, batch=args.batch
    ):
        print(f"{repr(result)}")


if __name__ == "__main__":
    asyncio.run(main())
