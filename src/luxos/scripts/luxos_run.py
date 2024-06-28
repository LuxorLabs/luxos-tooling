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

from luxos import misc, utils

from ..cli import v1 as cli

log = logging.getLogger(__name__)


def add_arguments(parser: cli.LuxosParserBase) -> None:
    cli.flags.add_arguments_new_miners_ips(parser)
    cli.flags.add_arguments_rexec(parser)
    parser.add_argument("script", type=Path, help="python script to run")
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
    module = misc.loadmod(args.script)
    if not hasattr(module, "main"):
        args.error(f"no entry point main in {args.script}")

    result = {}
    for data in await utils.launch(args.addresses, module.main, raw=False):
        if isinstance(data, utils.LuxosLaunchTimeoutError):
            log.warning("timeout error connecting to %s", data.address)
        elif isinstance(data, utils.LuxosLaunchError):
            log.warning("failed to fetch data from %s: \n%s", data.address, data.tback)
        else:
            result[data.address] = data.data

    if args.json:
        print(json.dumps(result, indent=2))
    if args.pickle:
        args.pickle.write_bytes(pickle.dumps(result))


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
