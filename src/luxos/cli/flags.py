"""various argparse `type` attributes"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import logging
from pathlib import Path
from typing import Any, Sequence

from .shared import LuxosParserBase


def type_range(txt: str) -> Sequence[tuple[str, int | None]]:
    """type conversion for ranges

    This will enforce conversion between a string and a ranged object.

    Eg.
        parser.add_argument("--range", type=type_range)

        The --range argument will be:
            127.0.0.1  # single ip address
            127.0.0.1:1234  # single ip address with port
            127.0.0.1-127.0.0.3 # a list of (ip, port) tuple between *.1 and.3

        Alternatively you can pass a @filename to read data from a csv file
    """
    from luxos.ips import iter_ip_ranges, load_ips_from_csv, load_ips_from_yaml

    path = None
    if txt.startswith("@") and not (path := Path(txt[1:])).exists():
        raise argparse.ArgumentTypeError(f"file not found {path}")

    if path:
        with contextlib.suppress(RuntimeError):
            return load_ips_from_yaml(path)

    try:
        if path:
            return load_ips_from_csv(path)
        return list(iter_ip_ranges(txt))
    except RuntimeError as exc:
        raise argparse.ArgumentTypeError(f"conversion failed '{txt}': {exc.args[0]}")
    except Exception as exc:
        raise argparse.ArgumentTypeError(
            f"unknown conversion failed for '{txt}'"
        ) from exc


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


def add_arguments_rexec(parser: LuxosParserBase):
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

    def callback(args: argparse.Namespace):
        from .. import asyncops

        asyncops.TIMEOUT = args.timeout
        asyncops.RETRIES = args.retries
        asyncops.RETRIES_DELAY = args.retries_delay

    parser.callbacks.append(callback)


def add_arguments_config(parser: LuxosParserBase):
    # find the CONFIGPATH, from the module then from luxos.cli.v*
    default = None
    for module in reversed(parser.modules):
        if not hasattr(module, "CONFIGPATH"):
            continue
        default = Path.cwd() / Path(module.CONFIGPATH).expanduser()
        break
    if default and default.is_relative_to(Path.cwd()):
        default = default.relative_to(Path.cwd())

    parser.add_argument(
        "-c",
        "--config",
        default=default,
        type=Path,
        help="path to a config file",
    )

    def callback(args: argparse.Namespace):
        args.config = args.config.absolute() if args.config else 1

    parser.callbacks.append(callback)


def add_arguments_logging(parser: LuxosParserBase):
    group = parser.add_argument_group("Logging", "Logging related options")
    group.add_argument("-v", "--verbose", action="count", help="report verbose logging")
    group.add_argument("-q", "--quiet", action="count", help="report quiet logging")

    def setup_logging(config: dict[str, Any], count: int) -> None:
        levelmap = [
            logging.WARNING,
            logging.INFO,
            logging.DEBUG,
        ]
        n = len(levelmap)

        # awlays start from info level
        level = logging.INFO

        # we can set the default start log level in LOGGING_CONFIG
        if config.get("level", None) is not None:
            level = config["level"]

        # we control if we go verbose or quite here
        index = levelmap.index(level) + count
        config["level"] = levelmap[max(min(index, n - 1), 0)]
        logging.basicConfig(**config)

    def callback(args: argparse.Namespace):
        config = {}
        for module in reversed(args.modules):
            if not hasattr(module, "LOGGING_CONFIG"):
                continue
            config.update(module.LOGGING_CONFIG)

        count = (args.verbose or 0) - (args.quiet or 0)
        setup_logging(config, count)
        delattr(args, "verbose")
        delattr(args, "quiet")

    parser.callbacks.append(callback)


def add_arguments_database(parser: LuxosParserBase):
    """
    takes a string on a command line and retunr a sa engine.

    This is mean to be used as type in add_arguments

    .. parse_args
    args.engine = firmware.cli.process_engine(args.engine)

    The text format can be:
    - a string that will resolve into a Path
    - any string for sqlalchemy.engine.url.make_url

    In the first case a sqlite engine pointing to text Path will be returned,
    in the second a regular engine.

    Example:
    -------
        >>> process_engine("foobar.db")
        >>> process_engine("postgresql+psycopg2://<user>:<password>@<host>/<db>"

    """

    group = parser.add_argument_group("database", "Database related options")
    group.add_argument("--db", dest="engine", help="sqlalchemy uri or filename")
    group.add_argument(
        "--db-create", action="store_true", help="create the db structures"
    )

    def callback(args: argparse.Namespace):
        from sqlalchemy import create_engine
        from sqlalchemy.engine.url import make_url
        from sqlalchemy.exc import ArgumentError

        if not args.engine or not args.engine.strip():
            return None

        engine = None
        with contextlib.suppress(ArgumentError):
            url = make_url(args.engine)
            engine = create_engine(url)
        args.engine = engine or create_engine(f"sqlite:///{args.engine}", echo=False)

    parser.callbacks.append(callback)
