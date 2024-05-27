"""various argparse `type` attributes"""

from __future__ import annotations

import argparse
import contextlib
import datetime


def type_range(txt: str) -> list[tuple[str, int | None]]:
    """type conversion for ranges

    This will enforce conversion between a string and a ranged object.

    Eg.
        parser.add_argument("--range", type=type_range)

        The --range argument will be:
            127.0.0.1  # single ip address
            127.0.0.1:1234  # single ip address with port
            127.0.0.1-127.0.0.3 # a list of (ip, port) tuple between *.1 and.3
    """
    from luxos.ips import iter_ip_ranges

    try:
        return list(iter_ip_ranges(txt))
    except RuntimeError as exc:
        raise argparse.ArgumentTypeError(f"conversion failed '{txt}': {exc.args[0]}")
    except Exception as exc:
        raise argparse.ArgumentTypeError(f"conversion failed for {txt}") from exc


def type_hhmm(txt: str):
    """type conversion for ranges

    This will enforce conversion between a string and datetime.time object.

    Eg.
        parser.add_argument("--time", type=type_hhmm)

        The --time format is HH:MM
    """
    if not txt:
        return
    with contextlib.suppress(ValueError, TypeError):
        hh, _, mm = txt.partition(":")
        hh1 = int(hh)
        mm1 = int(mm)
        return datetime.time(hh1, mm1)
    raise argparse.ArgumentTypeError(f"failed conversion into HH:MM for '{txt}'")


def add_arguments_rexec(parser: argparse.ArgumentParser) -> None:
    """adds the rexec timing for timeout/retries/delays

    Ex.

    def add_arguments(parser):
        cli.flags.add_arguments_rexec(parser)

    def process_args(args):
        asyncops.TIMEOUT = args.timeout
        asyncops.RETRIES = args.retries
        asyncops.RETRIES_DELAY = args.retries_delay
        return args
    """
    from ..asyncops import RETRIES, RETRIES_DELAY, TIMEOUT

    group = parser.add_argument_group(
        "Remote execution", "rexec remote execution limits/timeouts"
    )
    group.add_argument(
        "--timeout", type=float, default=TIMEOUT, help="Timeout for each command"
    )
    group.add_argument(
        "--retries",
        type=int,
        default=RETRIES,
        help="Maximum number of retries for each command",
    )
    group.add_argument(
        "--retries-delay",
        type=float,
        default=RETRIES_DELAY,
        help="Delay in s between retries",
    )
