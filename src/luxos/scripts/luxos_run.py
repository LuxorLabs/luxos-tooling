"""Script to issue commands to miner(s)

This tool is designed to issue a simple command (with parameters) to a set of miners
defined on the command line (--range/--range_start/--range-end) or in a file (yaml/csv).

It loads a `script` file and execute across all the defined miners.

Eg.
```shell

# my-script.py
from luxos import asyncops
async def main(host: str, port: int):
    res = await asyncops.rexec(host, port, "version")
    return asyncops.validate(host, port, res, "VERSION")[0]

# in the cli
$> luxos-run --range 127.0.0.1 my-script.py --json
```

"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import pickle
from pathlib import Path

from luxos import misc, text, utils

from ..cli import v1 as cli

log = logging.getLogger(__name__)


def add_arguments(parser: cli.LuxosParserBase) -> None:
    cli.flags.add_arguments_new_miners_ips(parser)
    cli.flags.add_arguments_rexec(parser)
    parser.add_argument("script", type=Path, help="python script to run")
    parser.add_argument(
        "-e",
        "--entry-point",
        dest="entrypoint",
        help="script entry point",
        default="main",
    )
    parser.add_argument(
        "-t", "--tear-down", dest="teardown", help="script tear down function"
    )
    parser.add_argument("-n", "--batch", type=int, help="limit parallel executions")
    parser.add_argument(
        "--list", action="store_true", help="just display the machine to run script"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--json", action="store_true", help="json output")
    group.add_argument("--pickle", type=Path, help="pickle output")


def process_args(args: argparse.Namespace):
    if not args.addresses:
        args.error("need a miners flag (eg. --range/--ipfile)")
    if not args.script.exists():
        args.error(f"missings script file {args.script}")


@cli.cli(add_arguments=add_arguments, process_args=process_args)
async def main(args: argparse.Namespace):
    if args.list:
        for address in args.addresses:
            print(address)
        return
    module = misc.loadmod(args.script)

    entrypoint = getattr(module, args.entrypoint, None)
    if not entrypoint:
        args.error(f"no entry point {args.entrypoint} in {args.script}")
        return

    teardown = None
    if args.teardown:
        if not hasattr(module, args.teardown):
            args.error(f"no tear down function {args.teardown} in {args.script}")
        teardown = getattr(module, args.teardown, None)

    result = {}

    def callback(result):
        log.info("processed %i / %i", len(result), len(args.addresses))

    for data in await utils.launch(
        args.addresses, entrypoint, batch=args.batch, asobj=True, callback=callback
    ):
        if isinstance(data, utils.LuxosLaunchTimeoutError):
            log.warning(
                "failed connection to %s: %s\n%s",
                data.address,
                data.brief,
                text.indent(data.traceback or "", "| "),
            )
        elif isinstance(data, utils.LuxosLaunchError):
            log.warning(
                "insternal error from %s: %s\n%s",
                data.address,
                data.brief,
                text.indent(data.traceback or "", "| "),
            )
        else:
            result[data.address] = data.data

    if args.json:
        print(json.dumps(result, indent=2))
    if args.pickle:
        args.pickle.write_bytes(pickle.dumps(result))

    if teardown:
        teardown()


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
