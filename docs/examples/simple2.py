import argparse
import asyncio

import luxos.cli.v1 as cli


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-x", type=int, default=0, help="set the x flag")


def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    args.x = 2 * args.x


@cli.cli(add_arguments, process_args)
async def main(args: argparse.Namespace):
    """a simple test script with a simple description"""
    print(f"Got for x='{args.x}'")


if __name__ == "__main__":
    asyncio.run(main())
