## luxos.cli.v1

This module contains a `v1.cli` wrapper for a generic cli script.

It provides the script with some default flags such as:

* `-v/--verbose | -q/--quiet` flags to increase the logging verbosity level
* `-c/--config` to pass a config file (default to config.yaml)


### The simplest simple.py cli script
This is the barebone script, mean for a quick startup.

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
INFO:__main__:an info message, you can silence it with -q|--quiet
WARNING:__main__:a warning!
INFO:luxos.cli.v1:task completed in 0.00s
```

Plese note:

- by default only info/warning/error/exception levels are reported
- you can change the *verbosity* or *quiet* level passing -v|-q flags
- at the end of the execution there's a timing report
- args contains the attributes passed to the script (more later)

