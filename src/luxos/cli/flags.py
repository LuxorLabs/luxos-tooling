"""
a collection of argparse `type_*` and 'add_arguments_*' functions

This is a collection of functions can be used with argparser add_argumnet
and parser.

Eg.::

    # this will validate the `-x` value as HH:MM to datetime.time
    parser.add_argument("-x", type=type_hhmm)

Or::

    # this will add few arguments to the parser
    add_arguments_rexec(parser)

"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import logging
from pathlib import Path
from typing import Any, Sequence

from .shared import ArgumentTypeBase, LuxosParserBase


class type_ipaddress(ArgumentTypeBase):
    """
    Validate a type as an ip addresses.

    Raises:
        argparse.ArgumentTypeError: on an invalid input.

    Returns:
        tuple[str, None | int] or None

    Example:
        file.py::

            parser.add_argument("-x", type=type_ipaddress)
            options = parser.parse_args()
            ...

            assert options.x == ("host", 9999)


        shell::

            file.py -x host:9999
    """

    def validate(self, txt) -> None | tuple[str, None | int]:
        from luxos import ips

        if txt is None:
            return None
        try:
            result = ips.parse_expr(txt) or ("", "", None)
            if result[1]:
                raise argparse.ArgumentTypeError("cannot use a range as expression")
            return (result[0], result[2])
        except ips.AddressParsingError as exc:
            raise argparse.ArgumentTypeError(f"failed to parse {txt=}: {exc.args[0]}")


def type_range(txt: str) -> Sequence[tuple[str, int | None]]:
    """
    Validate a range of ip addresses.

    Raises:
        argparse.ArgumentTypeError: on an invalid input.

    Returns:
        Sequence[tuple[str, int | None]]

    Example:
        file.py::

            parser.add_argument("-x", type=type_range)
            options = parser.parse_args()
            ...

            assert options.x == [
                ("127.0.0.1", 9999),
                ("127.0.0.2", 9999),
                ("127.0.0.3", 9999),
            ]


        shell::

            file.py -x 127.0.0.1:9999:127.0.0.3

        Alternatively you can pass a **@filename** to read data from a csv file
    """
    from luxos.ips import (
        DataParsingError,
        iter_ip_ranges,
        load_ips_from_csv,
        load_ips_from_yaml,
    )

    path = None
    if txt.startswith("@") and not (path := Path(txt[1:])).exists():
        raise argparse.ArgumentTypeError(f"file not found {path}")
    if Path(txt).exists():
        path = Path(txt)

    if path:
        with contextlib.suppress(RuntimeError, DataParsingError):
            return load_ips_from_yaml(path, None)

    try:
        if path:
            return load_ips_from_csv(path, None)
        return list(iter_ip_ranges(txt))
    except RuntimeError as exc:
        raise argparse.ArgumentTypeError(f"conversion failed '{txt}': {exc.args[0]}")
    except Exception as exc:
        raise argparse.ArgumentTypeError(
            f"unknown conversion failed for '{txt}'"
        ) from exc


class type_hhmm(ArgumentTypeBase):
    """
    Validate a type as a datetime.time in HH:MM format

    Raises:
        argparse.ArgumentTypeError: on an invalid input.

    Returns:
        datetime.time or None

    Example:
        file.py::

            parser.add_argument("-x", type=type_hhmm)
            options = parser.parse_args()
            ...

            assert options.x == datetime.time(12, 13)


        shell::

            file.py -x 12:13
    """

    def validate(self, txt) -> None | datetime.time:
        if not txt:
            return None
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
        from .. import asyncops, syncops

        asyncops.TIMEOUT = syncops.TIMEOUT = args.timeout
        asyncops.RETRIES = syncops.RETRIES = args.retries
        asyncops.RETRIES_DELAY = syncops.RETRIES_DELAY = args.retries_delay

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


def add_arguments_new_miners_ips(parser: LuxosParserBase):
    group = parser.add_argument_group("Miners", "miners list or range")
    group.add_argument(
        "--range",
        action="append",
        dest="addresses",
        help="IPs range or @file",
        type=type_range,
    )
    group.add_argument(
        "--port", dest="port", help="miners' default port", type=int, default=4028
    )

    def callback(args: argparse.Namespace):
        addresses = []
        if args.addresses:
            addresses.extend(
                [
                    (host, port or args.port)
                    for group in args.addresses
                    for host, port in group
                ]
            )
        args.addresses = addresses

    parser.callbacks.append(callback)
