"""cli utilities

This is the v1.cli decorator to help writing cli scripts with a consistent
interface.

A simple v1 script will always have:
* `-v/--verbose | -q/--quiet` flags to increase the logging verbosity level
* `-c/--config` to pass a config file (default to config.yaml)

A `sample.py` script with default sensible and consistent interface:

```
import argparse
import luxos.cli.v1 as cli
import logging

log = logging.getLogger(__name__)


@cli.cli()
def main(args: argparse.Namespace):
    log.debug("a debug message, need to use -v|--verbose to display it")
    log.info("an info message, you can silence it with -q|--quiet")
    log.warning("a warning!")


if __name__ == "__main__":
    main()
```


### Advanced usages

#### changing the default config file

In the `sample.py` file, just add:

```
CONFIGPATH = "my.config.file.yaml"
```

`CONFIGPATH` is part of the module level "magic" variables.

Another one is `LOGGING_CONFIG` (not recommended!):
```
LOGGING_CONFIG = {
    'level': logging.INFO,
    'format': "%(asctime)s:%(name)s:[%(levelname)s] %(message)s",
    'handlers': [
        logging.StreamHandler(),
        logging.FileHandler("LuxOS-LoadControl.log")
    ],
}
```

The `LOGGING_CONFIG` is a dictionary feed into `logging.basicConfig(**LOGGING_CONFIG)`.

#### add and process new extra arguments

in the `sample.py` file:

```
def add_arguments(parser: argparse.ArgumentParser) -> None:
    ... adds as many args needed


def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    ... you can manipulate args in place, changing its attributes in place
    ... if you return a new Namespace instance then it will be fee to main below


@cli.cli(add_arguments, process_args)
def main(args: argparse.Namespace):
    ... args is the Namespace instance returned by process_args if defined,
    ... or the default processed one of process_args is not provided

```

#### escape hatch to handle all the parsing/processing

```

@cli.cli()
def main(parser: argparse.ArgumentParser):
    ... you can use directly the parser here

```

"""

from __future__ import annotations

import argparse
import contextlib
import functools
import inspect
import logging.handlers
import sys
import time
import types
from pathlib import Path
from typing import Any, Callable

from . import flags
from .shared import LuxosParserBase


class MyHandler(logging.StreamHandler):
    def emit(self, record):
        record.shortname = record.levelname[0]
        return super().emit(record)


# SPECIAL MODULE LEVEL VARIABLES
LOGGING_CONFIG = {
    "format": "%(asctime)s [%(shortname)s] %(name)s: %(message)s",
    "handlers": [
        MyHandler(),
    ],
}
CONFIGPATH = Path("config.yaml")


log = logging.getLogger(__name__)


class CliBaseError(Exception):
    pass


class AbortCliError(CliBaseError):
    pass


class AbortWrongArgumentError(CliBaseError):
    pass


def log_sys_info(modules=None):
    from luxos.version import get_version

    log.debug(get_version())
    log.debug("interpreter: %s", sys.executable)


ArgumentParser = LuxosParserBase


class LuxosParser(LuxosParserBase):
    def __init__(self, modules: list[types.ModuleType], *args, **kwargs):
        from luxos.version import get_version

        super().__init__(modules, *args, **kwargs)

        # we're adding the -v|-q flags, to control the logging level
        flags.add_arguments_logging(self)

        # and a --version flag
        self.add_argument("--version", action="version", version=get_version(modules))

    def error(self, message: str):
        raise AbortWrongArgumentError(message)

    def parse_args(self, args=None, namespace=None):
        options = super().parse_args(args, namespace)

        # reserver attributes
        for reserved in [
            "modules",
            "error",
        ]:
            if not hasattr(options, reserved):
                continue
            raise RuntimeError(f"cannot add an argument with dest='{reserved}'")
        options.error = self.error
        options.modules = self.modules

        for callback in self.callbacks:
            if not callback:
                continue
            options = callback(options) or options

        log_sys_info(self.modules)
        return options

    @classmethod
    def get_parser(cls, modules: list[types.ModuleType], **kwargs):
        class Formatter(
            argparse.RawTextHelpFormatter,
            argparse.RawDescriptionHelpFormatter,
            argparse.ArgumentDefaultsHelpFormatter,
        ):
            pass

        return cls(modules, formatter_class=Formatter, **kwargs)


@contextlib.contextmanager
def setup(
    function: Callable,
    add_arguments: (
        Callable[[LuxosParserBase], None]
        | Callable[[argparse.ArgumentParser], None]
        | None
    ) = None,
    process_args: (
        Callable[[argparse.Namespace], argparse.Namespace | None] | None
    ) = None,
):
    from luxos.version import get_version

    sig = inspect.signature(function)
    module = inspect.getmodule(function)

    if "args" in sig.parameters and "parser" in sig.parameters:
        raise RuntimeError("cannot use args and parser at the same time")

    description, _, epilog = (
        (function.__doc__ or module.__doc__ or "").strip().partition("\n")
    )
    epilog = f"{description}\n{'-'*len(description)}\n{epilog}"
    description = ""

    kwargs = {}
    modules = [
        sys.modules[__name__],
    ]
    if module:
        modules.append(module)
    parser = LuxosParser.get_parser(modules, description=description, epilog=epilog)
    if add_arguments and (callbacks := add_arguments(parser)):
        if isinstance(callbacks, list):
            parser.callbacks.extend(callbacks)
        else:
            parser.callbacks.append(callbacks)

    if "parser" in sig.parameters:
        kwargs["parser"] = parser

    t0 = time.monotonic()
    success = "completed"
    errormsg = ""
    show_timing = True
    try:
        if "parser" not in sig.parameters:
            args = parser.parse_args()
            if process_args:
                args = process_args(args) or args

            if "args" in sig.parameters:
                kwargs["args"] = args
        yield sig.bind(**kwargs)
    except AbortCliError as exc:
        show_timing = False
        if exc.args:
            print(str(exc), file=sys.stderr)
        sys.exit(2)
    except AbortWrongArgumentError as exc:
        show_timing = False
        parser.print_usage(sys.stderr)
        print(f"{parser.prog}: error: {exc.args[0]}", file=sys.stderr)
        sys.exit(2)
    except SystemExit as exc:
        show_timing = False
        sys.exit(exc.code)
    except Exception:
        log.exception("un-handled exception")
        success = f"failed ({get_version(modules)})"
    finally:
        if show_timing:
            delta = round(time.monotonic() - t0, 2)
            log.debug("task %s in %.2fs", success, delta)
    if errormsg:
        parser.error(errormsg)


def cli(
    # add_arguments: Callable[[LuxosParserBase | argparse.ArgumentParser], Any]
    add_arguments: (
        Callable[[LuxosParserBase], Any]
        | Callable[[argparse.ArgumentParser], Any]
        | None
    ) = None,
    process_args: (
        Callable[[argparse.Namespace], argparse.Namespace | None] | None
    ) = None,
):
    def _cli1(function):
        module = inspect.getmodule(function)

        if inspect.iscoroutinefunction(function):

            @functools.wraps(function)
            async def _cli2(*args, **kwargs):
                with setup(function, add_arguments, process_args) as ba:
                    return await function(*ba.args, **ba.kwargs)

        else:

            @functools.wraps(function)
            def _cli2(*args, **kwargs):
                with setup(function, add_arguments, process_args) as ba:
                    return function(*ba.args, **ba.kwargs)

        _cli2.attributes = {
            "doc": function.__doc__ or module.__doc__ or "",
        }
        return _cli2

    return _cli1
