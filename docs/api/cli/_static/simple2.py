"""
A script to show how to add and process extra arguments.

Example:

    $> python simple2.py -q 12
    the args.x is 6

    $> python simple2 -x 3 --range 127.0.0.1-127.0.0.3 --quiet
    the args.x is 6
    the args.range is:
      ('127.0.0.1', None)
      ('127.0.0.2', None)
      ('127.0.0.3', None)
"""

import argparse
import asyncio

import luxos.cli.v1 as cli

# This is the default, it can be omitted
CONFIGPATH = "config.yaml"


def add_arguments(
    parser: cli.ArgumentParser,
):
    # this adds an int flag
    parser.add_argument("-x", type=int, dest="mult", default=1, help="set the x flag")

    # this is an int argument
    parser.add_argument("number", type=int)

    # cli.flags contain various "type_*" you can use
    # this validates the input to the flag as HHMM
    parser.add_argument("--time", type=cli.flags.type_hhmm)

    # also it contains "add_arguments_*" adding multiple flags
    # this will add a -c|--config file
    cli.flags.add_arguments_config(parser)
    cli.flags.add_arguments_new_miners_ips(parser)


def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    # we double anything we receive from user
    args.number *= args.mult


@cli.cli(add_arguments, process_args)
async def main(args: argparse.Namespace):
    print(f"the args.mult is args.mult={args.mult}")
    print(f"the final result is args.number={args.number}")
    print(f"args.config={args.config}")
    print(args.time)


if __name__ == "__main__":
    asyncio.run(main())
