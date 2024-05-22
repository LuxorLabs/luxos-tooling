"""this line will be reported as 'description'

More lines will be put in the help message. You can
put a larger description, some comments and an example here.
"""

import argparse
import logging

import luxos.cli.v1 as cli

log = logging.getLogger(__name__)


@cli.cli()
def main(args: argparse.Namespace):
    log.debug("a debug message, need to use -v|--verbose to display it")
    log.info("an info message, you can silence it with -q|--quiet")
    log.warning("a warning!")


if __name__ == "__main__":
    main()
