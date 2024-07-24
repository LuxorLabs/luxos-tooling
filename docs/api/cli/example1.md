# example 1
XX
:Internal file reference: [XX](_static/simple1.py)

This is the most basic cli script, showing the basics.

```python
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
```

The help message:
```bash
$> python docs/examples/simple1.py --help
usage: simple1.py [-h] [-v] [-q] [-c CONFIG]

this line will be reported as 'description'

options:
  -h, --help            show this help message and exit
  -v, --verbose         report verbose logging (default: None)
  -q, --quiet           report quiet logging (default: None)
  -c CONFIG, --config CONFIG
                        path to a config file (default: config.yaml)

More lines will be put in the help message. You can
put a larger description, some comments and an example here.
```


Calling from the command line this script will output:
```
INFO:__main__:an info message, you can silence it by passing with -q|--quiet
WARNING:__main__:a warning!
INFO:luxos.cli.v1:task completed in 0.00s
```

Plese note:
> NOTE:
> - the script has some default flags eg. `--verbose|--quiet|--config`
> - `--verbose|--quiet` flags control the logging level (by default set to logging.INFO)
> - at the end of the execution there's a timing report
> - `args` is a argparse.Namespace instance containing the "arguments" coming from the cli

