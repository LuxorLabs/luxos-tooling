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

# SPECIAL MODULE LEVEL VARIABLES
MODULE_VARIABLES = {
    "LOGGING_CONFIG": None,
}


log = logging.getLogger(__name__)


class LuxosParser(argparse.ArgumentParser):
    def __init__(self, module_variables, *args, **kwargs):
        self.module_variables = module_variables or {}
        super().__init__(*args, **kwargs)
        self.add_argument(
            "-v", "--verbose", action="count", help="report verbose logging"
        )
        self.add_argument("-q", "--quiet", action="count", help="report quiet logging")
        self.add_argument(
            "-c",
            "--config",
            default=Path("config.yaml"),
            type=Path,
            help="load yaml config file",
        )

    def parse_args(self, args=None, namespace=None):
        options = super().parse_args(args, namespace)
        options.error = self.error

        # set the logging level
        count = (options.verbose or 0) - (options.quiet or 0)
        level = {
            1: logging.DEBUG,
            0: logging.INFO,
            -1: logging.WARNING,
        }[max(min(count, 1), -1)]

        module_variables = self.module_variables
        config = {}
        if value := module_variables.get("LOGGING_CONFIG"):
            config = value.copy()
        config["level"] = level
        logging.basicConfig(**config)

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
            try:
                if "parser" not in sig.parameters:
                    args = parser.parse_args()
                    if process_args:
                        args = process_args(args) or args
                    if "args" in sig.parameters:
                        kwargs["args"] = args
                yield sig.bind(**kwargs)
            except Exception:
                log.exception("un-handled exception")
                success = "failed"
            finally:
                delta = round(time.monotonic() - t0, 2)
                log.info("task %s in %.2fs", success, delta)

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
