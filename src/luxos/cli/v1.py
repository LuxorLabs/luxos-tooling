"""cli utilities

This adds a `cli` decorator to make easier to write consistent scripts.

It adds:
    -v/--verbose/-q/--quiet flags to increase the logging verbosity level
    -c/--config to pass a config file (default to config.yaml)

Eg. in your script
    from luxos_firmware.cli.v1 import cli

    # this is the plain calling function
    @cli()
    def main(args):
        ... args is a argparse.Namespace

    # This call allows to add arguments to the parser

    def add_arguments(parser):
        parser.add_argument(....

    def process_args(args):
        ...

    @cli(add_arguments, process_args)
    @def main(args):
        ... args is a argparse.Namespace

    # finally this will let you control the parser
    @cli()
    def main(parser):
        parser.add_argument()
        args = parser.parse_args()
"""

from __future__ import annotations

import contextlib
import inspect
import logging
import time
from pathlib import Path
import functools
import argparse
from typing import Any


# SPECIAL MODULE LEVEL VARIABLES
MODULE_VARIABLES = {
    "LOGGING_CONFIG": None,  # logging config dict (passed to logging.basicConfig(**LOGGING_CONFIG))
    "CONFIGPATH": Path("config.yaml"),  # config default path
}


log = logging.getLogger(__name__)


class CliBaseError(Exception):
    pass


class AbortCliError(CliBaseError):
    pass


def setup_logging(count: int, config: dict[str, Any]) -> None:
    levelmap = {
        1: logging.DEBUG,
        0: logging.INFO,
        -1: logging.WARNING,
    }

    # we can set the default log level in LOGGING_CONFIG
    if config.get("level", None) is not None:
        levelmap[0] = config["level"]

    config["level"] = levelmap[count]
    logging.basicConfig(**config)


class LuxosParser(argparse.ArgumentParser):
    def __init__(self, module_variables, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.module_variables = module_variables or {}

        # we're adding the -v|-q flags, to control the logging level
        self.add_argument(
            "-v", "--verbose", action="count", help="report verbose logging"
        )
        self.add_argument("-q", "--quiet", action="count", help="report quiet logging")

        # we add the -c|--config flag to point to a config file
        configpath = (
            self.module_variables.get("CONFIGPATH") or MODULE_VARIABLES["CONFIGPATH"]
        )
        configpath = Path(configpath).expanduser().absolute()
        if configpath.is_relative_to(Path.cwd()):
            configpath = configpath.relative_to(Path.cwd())

        self.add_argument(
            "-c",
            "--config",
            default=configpath,
            type=Path,
            help="path to a config file",
        )

    def parse_args(self, args=None, namespace=None):
        options = super().parse_args(args, namespace)

        # we provide an error function to nicely bail out the script
        options.error = self.error

        # setup the logging
        config = {}
        if value := self.module_variables.get("LOGGING_CONFIG"):
            config = value.copy()

        count = max(min((options.verbose or 0) - (options.quiet or 0), 1), -1)
        setup_logging(count, config)

        return options

    @classmethod
    def get_parser(cls, module_variables):
        class Formatter(
            argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter
        ):
            pass

        return cls(module_variables=module_variables, formatter_class=Formatter)


def cli(add_arguments=None, process_args=None):
    def _cli1(function):
        @contextlib.contextmanager
        def setup():
            sig = inspect.signature(function)

            module_variables = MODULE_VARIABLES.copy()
            module = inspect.getmodule(function)
            for name in list(module_variables):
                module_variables[name] = getattr(module, name, None)

            if "args" in sig.parameters and "parser" in sig.parameters:
                raise RuntimeError("cannot use args and parser at the same time")

            kwargs = {}
            parser = LuxosParser.get_parser(module_variables)
            if add_arguments:
                add_arguments(parser)

            if "parser" in sig.parameters:
                kwargs["parser"] = parser

            t0 = time.monotonic()
            success = "completed"
            errormsg = ""
            try:
                if "parser" not in sig.parameters:
                    args = parser.parse_args()
                    if process_args:
                        args = process_args(args) or args
                    if "args" in sig.parameters:
                        kwargs["args"] = args
                yield sig.bind(**kwargs)
            except AbortCliError as exc:
                errormsg = str(exc)
                success = "failed"
            except Exception:
                log.exception("un-handled exception")
                success = "failed"
            finally:
                delta = round(time.monotonic() - t0, 2)
                log.info("task %s in %.2fs", success, delta)
            if errormsg:
                parser.error(errormsg)

        if inspect.iscoroutinefunction(function):

            @functools.wraps(function)
            async def _cli2(*args, **kwargs):
                with setup() as ba:
                    return await function(*ba.args, **ba.kwargs)
        else:

            @functools.wraps(function)
            def _cli2(*args, **kwargs):
                with setup() as ba:
                    return function(*ba.args, **ba.kwargs)

        return _cli2

    return _cli1
