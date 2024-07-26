#!/usr/bin/env python3
"""
This is the simplest script leveraging luxos.cli package.

Lines here will be put in the help message. You can
put a larger description, some comments and an example here.

Here are shown:
1. the basic initialization
2. how to control the logging

Examples:

    $> simple1.py --quiet
    2024-06-01 07:16:35,413 [W] __main__: a warning!
"""

import argparse
import logging

import luxos.cli.v1 as cli

log = logging.getLogger(__name__)

# this is the default, here just for display
LOGGING_CONFIG = {
    "level": logging.INFO,  # This is the default
}


@cli.cli()
def main(args: argparse.Namespace):
    # show some logging info
    log.debug("a debug message, need to use -v|--verbose to display it")
    log.info("an info message, you can silence it with -q|--quiet")
    log.warning("a warning!")

    # args is a argparse.Namespace instance. Attributes always defined are:
    #   .config - points to a config file might be present or not
    #   .error - callable, to abort a script with a nice error message
    #   .modules - list of modules leading to this script

    print("args:")
    for name in dir(args):
        if name.startswith("_"):
            continue
        value = getattr(args, name)
        kind = type(value)
        if name == "error":
            kind, value = "callable", "abort a script with an error message"
        print(f"  .{name}: ({kind}) {value}")


if __name__ == "__main__":
    main()
