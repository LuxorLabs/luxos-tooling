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
import functools
import inspect
import json
import logging
import pickle
import urllib.parse
from pathlib import Path
from typing import Any, Callable

import tqdm

from luxos import misc, text, utils

from ..cli import v1 as cli

log = logging.getLogger(__name__)


def add_arguments(parser: cli.LuxosParserBase) -> None:
    cli.flags.add_arguments_new_miners_ips(parser)
    cli.flags.add_arguments_rexec(parser)
    parser.add_argument("script", type=Path, help="python script to run")
    parser.add_argument("parameters", nargs="*")

    parser.add_argument("-s", "--setup", help="script setup up function (non async)")
    parser.add_argument(
        "-e", "--entry-point", dest="entrypoint", help="script entry point"
    )
    parser.add_argument(
        "-t", "--teardown", help="script tear down function (non async)"
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

    if urllib.parse.urlparse(str(args.script)).scheme not in {"http", "https"}:
        if not args.script.exists():
            args.error(f"missings script file {args.script}")
        if args.script.suffix.upper() not in {".PY"}:
            args.error(f"script must end with .py: {args.script}")


def apply_magic_arguments(fn: Callable, magic: dict[str, Any]) -> Callable:
    sig = inspect.signature(fn)
    arguments = sig.bind_partial(
        **{k: v for k, v in magic.items() if k in sig.parameters}
    )
    return functools.partial(fn, *arguments.args, **arguments.kwargs)


@cli.cli(add_arguments=add_arguments, process_args=process_args)
async def main(args: argparse.Namespace):
    if args.list:
        for address in args.addresses:
            print(address)
        return

    # load the module
    module = misc.loadmod(args.script)

    # assign the setup/entrypoint/teardown functions
    setup = None
    if args.setup != "":
        setup = getattr(module, args.setup or "setup", None)
        if args.setup and not setup:
            args.error(f"no setup function {args.setup} in {args.script}")
    log.debug(
        "%susing setup function%s",
        "" if setup else "not ",
        f" {setup}" if setup else "",
    )

    if not (entrypoint := getattr(module, args.entrypoint or "main", None)):
        args.error(f"no entry point {args.entrypoint or 'main'} in {args.script}")
    if not inspect.iscoroutinefunction(entrypoint):
        args.error(
            f"entry point is not an async function: {args.entrypoint} in {args.script}"
        )

    if set(inspect.signature(entrypoint).parameters) - {"host", "port"}:  # type: ignore
        args.error(
            f"entry point {args.entrypoint or 'main'} function "
            "must have (host, port) signature"
        )
    log.debug("using entrypoint function %s", entrypoint)

    teardown = None
    if args.teardown != "":
        teardown = getattr(module, args.teardown or "teardown", None)
        if args.teardown and not teardown:
            args.error(f"no teardown function {args.teardown} in {args.script}")
    log.debug(
        "%susing teardown function%s",
        "" if teardown else "not ",
        f" {teardown}" if teardown else "",
    )

    # these are magic values passed to all setup/main/teardown functions
    magic = {"addresses": args.addresses, "parameters": args.parameters, "result": {}}

    # ok, execute here

    if setup:
        apply_magic_arguments(setup, magic)()

    progress = tqdm.tqdm(total=len(args.addresses))

    def callback(addresses):
        progress.update(len(addresses))

    result = magic["result"]
    for data in await utils.launch(
        args.addresses,
        entrypoint,  # type: ignore
        batch=args.batch,
        asobj=True,
        callback=callback,
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
                "internal error from %s: %s\n%s",
                data.address,
                data.brief,
                text.indent(data.traceback or "", "| "),
            )
        else:
            result[data.address] = data.data

    if teardown:
        result = apply_magic_arguments(teardown, magic)() or result

    if args.json:
        print(json.dumps(result, indent=2))
    if args.pickle:
        args.pickle.write_bytes(pickle.dumps(result))


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
