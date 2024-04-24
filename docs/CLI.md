## luxos.cli.v1

This module contains a `v1.cli` wrapper for a generic cli script.

It provides the script with some default flags such as:

* `-v/--verbose | -q/--quiet` flags to increase the logging verbosity level
* `-c/--config` to pass a config file (default to config.yaml)

TOC:
- [The simplest cli script](#the-simplest-cli-script)
- [Adding new flags and processing the arguments](#adding-new-flags-and-processing-the-arguments)

### The simplest cli script
This is the barebone script, mean for a quick startup.

**simple1.py**
```python

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

Calling from the command line this script will output:
```
INFO:__main__:an info message, you can silence it by passing with -q|--quiet
WARNING:__main__:a warning!
INFO:luxos.cli.v1:task completed in 0.00s
```

Plese note:

- by default only info/warning/error/exception levels are reported
- you can change the *verbosity* or *quiet* level by passing -v|-q flags
- at the end of the execution there's a timing report
- args contains the attributes passed to the script (more later)

### Adding new flags and processing the arguments
We can add new flags to the parser, processing the args returned by parsing the cli args
with few small changes.
**simple2.py**
```python
import argparse
import luxos.cli.v1 as cli
import logging

log = logging.getLogger(__name__)

def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-x", type=int, default=0, help="set the x flag")


def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    args.x = 2 * args.x


@cli.cli(add_arguments, process_args)
def main(args: argparse.Namespace):
    print(f"Got for x='{args.x}'")


if __name__ == "__main__":
    main()
```
Than calling the script will result in:
```bash
python simple2.py -q
Got for x='0'

python simple2.py -q -x 12
Got for x='24'
```
