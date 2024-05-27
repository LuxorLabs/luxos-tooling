"""script to show how to add process arguments

Example:
    $> python simple2
    Got for x='0'
    INFO:luxos.cli.v1:task completed in 0.00s

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


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-x", type=int, default=0, help="set the x flag")

    # using the internal range flag
    parser.add_argument(
        "--range", action="append", type=cli.flags.type_range, help="add ranged hosts"
    )

    # adds rexec flags
    cli.flags.add_arguments_rexec(parser)

    # add a new time flag
    parser.add_argument("--time", type=cli.flags.type_hhmm)


def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    args.x = 2 * args.x

    # we flatten all the addresses
    args.range = [a for r in args.range or [] for a in r]


@cli.cli(add_arguments, process_args)
async def main(args: argparse.Namespace):
    """a simple test script with a simple description"""

    # many ways to abort a script
    # 1. raising various exceptions
    #     (dump a stack trace)
    #     >>> raise RuntimeError("aborting")
    #     (dump a nice error message on the cli)
    #     >>> raise cli.AbortWrongArgument("a message)
    #     (abort unconditionally the application)
    #     >>> raise cli.AbortCliError("abort")
    # 2. using args.error (nice cli error message)
    #     >>> args.error("too bad")

    # logging to report messages
    log.debug("a debug message")
    log.info("an info message")
    log.warning("a warning message")

    # handle the args
    if args.range:
        print("args.range")
        for host, port in args.range or []:
            print(f"  {host}:{port}")
    for key in ["x", "time", "timeout", "max_retries", "delay_retry"]:
        if getattr(args, key, None) is not None:
            print(f"args.{key}: {getattr(args, key)} ({type(getattr(args, key))})")


if __name__ == "__main__":
    asyncio.run(main())
