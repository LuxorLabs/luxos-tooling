"""
A script to show how to add and process extra arguments.

Example:

    $> python simple2.py -q
    ...
    Got for x='0'
    ...

    $> python simple2 -x 3 --range 127.0.0.1-127.0.0.3
    Got for x='6'
      127.0.0.1:None
      127.0.0.2:None
      127.0.0.3:None
    INFO:luxos.cli.v1:task completed in 0.00s
"""

import argparse
import asyncio
import logging

import luxos.cli.v1 as cli

log = logging.getLogger(__name__)


def add_arguments(
    parser: argparse.ArgumentParser,
) -> cli.ArgsCallback | list[cli.ArgsCallback]:
    parser.add_argument("-x", type=int, default=0, help="set the x flag")

    # we add a --range flag to the script and validate the value
    parser.add_argument(
        "--range", action="append", type=cli.flags.type_range, help="add ranged hosts"
    )

    # adds all rexec related flags
    callback = cli.flags.add_arguments_rexec(parser)

    def callback2(args: argparse.Namespace):
        # you can post process the args
        pass

    # add a new time flag taking a HH:MM string (validates it)
    parser.add_argument("--time", type=cli.flags.type_hhmm)
    return [callback, callback2]


def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    # we double anything we receive from user
    args.x = 2 * args.x

    # we flatten all the addresses
    args.range = [a for r in args.range or [] for a in r]


@cli.cli(add_arguments, process_args)
async def main(args: argparse.Namespace):
    log.info("Loading config from %s", args.config)
    print(f"the args.x is {args.x}")

    # there many ways to abort a script
    # 1. raising various exceptions
    #     (dump a stack trace)
    #     >>> raise RuntimeError("aborting")
    #     (dump a nice error message on the cli)
    #     >>> raise cli.AbortWrongArgumentError("a message)
    #     (abort unconditionally the application)
    #     >>> raise cli.AbortCliError("abort")
    # 2. using args.error (nice cli error message)
    #     >>> args.error("too bad")


if __name__ == "__main__":
    asyncio.run(main())
