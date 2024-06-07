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

    $> simple1.py
    2024-06-01 07:16:50,911 [I] luxos.cli.v1: py[3.12.2], luxos[/]
    ...
    2024-06-01 07:16:50,911 [W] __main__: a warning!
    2024-06-01 07:16:50,911 [I] luxos.cli.v1: task completed in 0.00s

    $> simple1.py -v
    2024-06-01 07:17:17,379 [I] luxos.cli.v1: py[3.12.2], luxos[/]
    ...
    2024-06-01 07:17:17,379 [D] __main__: a debug message,
        need to use -v|--verbose to display it
    2024-06-01 07:17:17,379 [I] __main__: an info message,
        you can silence it with -q|--quiet
    2024-06-01 07:17:17,379 [W] __main__: a warning!
    ...
"""

import argparse
import logging

import luxos.cli.v1 as cli

log = logging.getLogger(__name__)


@cli.cli()  # this is the way
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
