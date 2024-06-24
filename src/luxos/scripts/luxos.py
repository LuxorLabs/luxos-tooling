"""Script to issue commands to miner(s)

This tool is designed to issue a simple command (with parameters) to a set of miners
defined on the command line (--range/--range_start/--range-end) or in a file (yaml/csv).
"""
from __future__ import annotations
import asyncio
import contextlib
import logging
import argparse
from pathlib import Path

from ..cli import v1 as cli
from ..syncops import execute_command

log = logging.getLogger(__name__)


def add_arguments(parser: cli.LuxosParserBase) -> None:

    def add_miners_arguments(group):
        group.add_argument("--range_start", help="IP start range")
        group.add_argument("--range_end", help="IP end range")
        group.add_argument("--ipfile", default=Path("ips.csv"), type=Path,
            help="File name to store IP addresses"
        )

        group.add_argument("--range", action="append", dest="addresses",
                           help="IPs range or @file", type=cli.flags.type_range)

        group.add_argument("--luxos-port", dest="luxos_port",
                           help="miners' default port", type=int, default=4028)
    group = parser.add_argument_group("Miners", "miners list or range")

    add_miners_arguments(group)
    cli.flags.add_arguments_rexec(parser)

    parser.add_argument("--cmd", "--command", dest="cmd", required=True, help="Command to execute on LuxOS API")
    parser.add_argument(
        "--params",
        dest="parameters",
        action="append",
        help="Parameters for LuxOS API (either str or key=value pair)",
    )
    parser.add_argument("--batch", dest="batchsize",
                        type=int, default=100,
                        help="limit execution to batch miners at time")

    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument(
        "-a",
        "--all",
        dest="details",
        action="store_const",
        const="all",
        help="show full result output",
    )
    group1.add_argument(
        "-j",
        "--json",
        dest="details",
        action="store_const",
        const="json",
        help="show results in json format",
    )


def process_args(args: argparse.Namespace):

    def process_addresses():  # yes, it is pretty long
        from luxos.ips import iter_ip_ranges, load_ips_from_csv
        args.addresses = [
            address for addresses in (args.addresses or []) for address in addresses
        ]

        # old way
        if args.range_start and args.range_end:
            args.addresses.extend(iter_ip_ranges(f"{args.range_start}-{args.range_end}"))
        elif args.range_start:
            args.addresses.append((args.range_start, None))
        elif args.range_end:
            args.error("--range_end requires --range_start")

        if args.ipfile.exists():
            args.addresses.extend(load_ips_from_csv(args.ipfile))

        args.addresses = [
            (host, port or args.luxos_port)
            for host, port in args.addresses
        ]

    process_addresses()
    if not args.addresses:
        args.error("need one of the miners group flags (eg. --range_{start|end}/--range")

    lparameters : list[str] = []
    dparameters : dict[str, str] = {}

    for param in args.parameters or []:
        if "=" in param:
            key, _, value = param.partition("=")
            if lparameters:
                args.error("--params can be all strings or key=value pairs, not mixed")
            dparameters[key] = value
        else:
            if dparameters:
                args.error("--params can be all strings or key=value pairs, not mixed")
            lparameters.append(param)
    args.parameters = lparameters or dparameters


@cli.cli(add_arguments=add_arguments, process_args=process_args)
async def main(args: argparse.Namespace):
    from . import async_luxos
    await async_luxos.run(
        args.addresses,
        cmd=args.cmd, params=args.parameters,
        batchsize=args.batchsize, delay=2.0, details=args.details
    )


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()