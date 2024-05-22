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

import luxos.cli.v1 as cli


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-x", type=int, default=0, help="set the x flag")

    # using the internal range flag
    parser.add_argument(
        "--range", action="append", type=cli.flags.type_range, help="add ranged hosts"
    )


def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    args.x = 2 * args.x

    # we flatten all the addresses
    args.range = [a for r in args.range or [] for a in r]


@cli.cli(add_arguments, process_args)
async def main(args: argparse.Namespace):
    """a simple test script with a simple description"""
    print(f"Got for x='{args.x}'")
    for host, port in args.range or []:
        print(f"  {host}:{port}")


if __name__ == "__main__":
    asyncio.run(main())
