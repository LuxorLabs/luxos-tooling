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
import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Any, Callable

from . import flags  # noqa: F401

# SPECIAL MODULE LEVEL VARIABLES
MODULE_VARIABLES = {
    "LOGGING_CONFIG": None,  # logging config dict
    # (passed to logging.basicConfig(**LOGGING_CONFIG))
    "CONFIGPATH": Path("config.yaml"),  # config default path
}

log = logging.getLogger(__name__)


class MyHandler(logging.StreamHandler):
    def emit(self, record):
        record.shortname = record.levelname[0]
        return super().emit(record)


LOGGING_CONFIG = {
    "format": "%(asctime)s [%(shortname)s] %(name)s: %(message)s",
    "handlers": [
        MyHandler(),
    ],
}


class CliBaseError(Exception):
    pass


class AbortCliError(CliBaseError):
    pass


class AbortWrongArgument(CliBaseError):
    pass


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

    config2 = LOGGING_CONFIG.copy()
    config2.update(config)
    logging.basicConfig(**config2)  # type: ignore


def log_sys_info():
    from luxos import __hash__, __version__

    log.info(
        "py[%s], luxos[%s/%s]", sys.version.partition(" ")[0], __version__, __hash__
    )
    log.debug("interpreter: %s", sys.executable)
    log.debug("version: %s", sys.version)


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
        if configpath:
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

    def error(self, message: str):
        raise AbortWrongArgument(message)

    def parse_args(self, args=None, namespace=None):
        options = super().parse_args(args, namespace)

        options.error = self.error

        # setup the logging
        config = {}
        if value := self.module_variables.get("LOGGING_CONFIG"):
            config = value.copy()

        count = (options.verbose or 0) - (options.quiet or 0)
        setup_logging(config, count)
        log_sys_info()
        return options

    @classmethod
    def get_parser(cls, module_variables, **kwargs):
        class Formatter(
            argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter
        ):
            pass

        return cls(
            module_variables=module_variables, formatter_class=Formatter, **kwargs
        )


def cli(
    add_arguments: Callable[[argparse.ArgumentParser], None] | None = None,
    process_args: (
        Callable[[argparse.Namespace], argparse.Namespace | None] | None
    ) = None,
):
    def _cli1(function):
        module = inspect.getmodule(function)

        @contextlib.contextmanager
        def setup():
            sig = inspect.signature(function)

            module_variables = MODULE_VARIABLES.copy()
            for name in list(module_variables):
                module_variables[name] = getattr(module, name, None)

            if "args" in sig.parameters and "parser" in sig.parameters:
                raise RuntimeError("cannot use args and parser at the same time")

            description, _, epilog = (
                (function.__doc__ or module.__doc__ or "").strip().partition("\n")
            )
            kwargs = {}
            parser = LuxosParser.get_parser(
                module_variables, description=description, epilog=epilog
            )
            if add_arguments:
                add_arguments(parser)

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
            except AbortWrongArgument as exc:
                show_timing = False
                parser.print_usage(sys.stderr)
                print(f"{parser.prog}: error: {exc.args[0]}", file=sys.stderr)
                sys.exit(2)
            except SystemExit as exc:
                show_timing = False
                sys.exit(exc.code)
            except Exception:
                log.exception("un-handled exception")
                success = "failed"
            finally:
                if show_timing:
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

        _cli2.attributes = {  # type: ignore[attr-defined]
            "doc": function.__doc__ or module.__doc__ or "",
        }
        return _cli2

    return _cli1
