"""Script to issue commands to miner(s)

This tool is designed to run commands to a set of miners defined on the command
line using the --range flag (either an ip address or a file prefixed with @.

Eg.

    # my-script.py
    from luxos import asyncops
    async def main(host: str, port: int):
        res = await asyncops.rexec(host, port, "version")
        return asyncops.validate(res, "VERSION", 1, 1)

    # in the cli
    $> luxos-run --range 127.0.0.1 --json my-script.py

NOTE:
  1. you can use multiple --range flags
  2. you can pass to --range flag a file (csv or yaml) using --range @file.csv
  3. ranges can specify a ip-start:ip-end
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import logging
import pickle
import sys
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
        "-t", "--teardown", dest="teardown", help="script tear down function"
    )
    parser.add_argument("-n", "--batch", type=int, help="limit parallel executions")
    parser.add_argument(
        "--list", action="store_true", help="just display the machine to run script"
    )

    group = parser.add_mutually_exclusive_group()
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

    # prepend the script dir to pypath
    log.debug("inserting %s in PYTHONPATH", args.script.parent)
    sys.path.insert(0, str(args.script.parent))

    module = misc.loadmod(args.script)

    entrypoint = getattr(module, args.entrypoint, None)
    if not entrypoint:
        args.error(f"no entry point {args.entrypoint} in {args.script}")
        return

    teardown = None
    if args.teardown == "":
        pass
    elif args.teardown:
        if not hasattr(module, args.teardown):
            args.error(f"no tear down function {args.teardown} in {args.script}")
        teardown = getattr(module, args.teardown, None)
    elif hasattr(module, "teardown"):
        teardown = getattr(module, "teardown")

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

    if teardown:
        if "result" in inspect.signature(teardown).parameters:
            newresult = teardown(result)
        else:
            newresult = teardown()
        result = newresult or result

    if args.json:
        print(json.dumps(result, indent=2))
    if args.pickle:
        args.pickle.write_bytes(pickle.dumps(result))


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
