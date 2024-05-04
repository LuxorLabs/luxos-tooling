## The command line tool luxos.cli.v1

Luxos comes with a convenient cli interface generator, similar to what [click](https://palletsprojects.com/p/click) provides,
but simplified for easier usage.

The tool is in the module `luxos.cli.v1`, and the `v1` denotes the first iteration of it. In future there 
might be more versions to accomodate different scenarios.

In the `v1` version a cli provides some default flags such as:

* `-v/--verbose | -q/--quiet` flags to increase the logging verbosity level
* `-c/--config` to pass a config file name (options, default to **config.yaml**)

Moreover it allows escape hatch to configure the cli on a per script base...
The examples:
- the simplest basic cli with documentation and logging 👉 [simple1](#examplessimple1py)
- adding custom arguments and processing them 👉 [simple2](#examplessimple2py)
- handling special script dependent configurations 👉 [simple3](#examplessimple3py)
- the smallest complete script 👉 [simple4](#examplesimple4py)

### Getting started

This is the most basic script for a quick startup.

#### examples/simple1.py

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

#### examples/simple2.py

On top of simple1.py, a cli might want to define extra arguments and or options, this is the way is done:

```python
import asyncio
import argparse

import luxos.cli.v1 as cli

def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-x", type=int, default=0, help="set the x flag")

def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    args.x = 2 * args.x

@cli.cli(add_arguments, process_args)
async def main(args: argparse.Namespace):
    """a simple test script with a simple description"""
    print(f"Got for x='{args.x}'")

if __name__ == "__main__":
    asyncio.run(main())
```

Calling the script will result in:
```bash
$> python simple2.py -q
Got for x='0'
```

```bash
$> python simple2.py -q -x 12
Got for x='24'
```

The parser processing works in this way:
```
parser creation
  -> adds default arguments (-q|-v|-c, internal)
  -> can use the add_arguments callback to cli.cli to add more arguments
  -> parser.parse_args() return args: argparse.Namespace()
  -> process_args(args) process args
args then is finally passed down to main(args).  
```

> **NOTE** argparse makes the distintion between options and arguments
> even if both get added to the parser using the same parser.add_argument method.
> 
> Basically it boils down to:
>
> *if it is required to run the script, then it is an argument*
>     -> you can parser.add_argument("argument")
> 
> *if it is NOT required to run the script, then it is an option*
>     -> you can parser.add_argument("--option")

#### examples/simple3.py

At the very begin we introduced three options (-v|-q|-c) predefined: while nice to have default values for
the log level and a default config file, some script might want to control those values in much finer detail.
For example the default logging just dumps the records to the stderr, it uses a simple default record emitter etc.

**cli.v1** defines some script level *magic* variables that can be used to configure those defaults.

```python
import argparse
import asyncio
import logging

import luxos.cli.v1 as cli

log = logging.getLogger(__name__)

CONFIGPATH = "booo.yaml"
LOGGING_CONFIG = {
    # the following forces the starting log level to WARNING, you can change using multiple -q|-v flags
    'level': logging.WARNING,
    'format': "%(asctime)s [%(levelname)s] %(message)s",
    'handlers': [
        # this will write the records to stderr and a log file
        logging.StreamHandler(),
        logging.FileHandler("LuxOS-LoadControl.log")
    ],
}


@cli.cli()
async def main(args: argparse.Namespace):
    log.debug("a debug message")
    log.info("an info message")
    log.warning("a warning!")

    # note as args.config is a pathlib.Path instance!
    print(f"Got: {args.config=}")


if __name__ == "__main__":
    asyncio.run(main())
```

Here:
- **CONFIGPATH** can point to an alternative configuration file
- **LOGGING_CONFIG** is a dictionary used as kwargs in basicConfig

The help reveals:
```bash
$> simple3.py --help
usage: simple3.py [-h] [-v] [-q] [-c CONFIG]

options:
  -h, --help            show this help message and exit
  -v, --verbose         report verbose logging (default: None)
  -q, --quiet           report quiet logging (default: None)
  -c CONFIG, --config CONFIG
                        path to a config file (default: booo.yaml)
```

The -c default argument is booo.yaml.

```bash
$> simple3.py
2024-05-03 20:09:26,920 [WARNING] a warning!
Got: args.config=PosixPath('booo.yaml')

$> simple3.py -vv
2024-05-03 20:10:00,552 [DEBUG] interpreter: /Users/antonio/venvs/luxos-tooling/bin/python
2024-05-03 20:10:00,552 [DEBUG] version: 3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]
2024-05-03 20:10:00,552 [DEBUG] a debug message
2024-05-03 20:10:00,552 [INFO] an info message
2024-05-03 20:10:00,552 [WARNING] a warning!
2024-05-03 20:10:00,552 [INFO] task completed in 0.00s
Got: args.config=PosixPath('booo.yaml')
```

#### examples/simple4.py

This is the smallest script that can execute commands across miners, supporting batch operations:

```python
import argparse
import asyncio
import logging

import luxos.cli.v1 as cli
from luxos import utils, misc

log = logging.getLogger(__name__)

CONFIGPATH = "miners.csv"


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("-b", "--batch", type=int, help="execute command limiting to batch concurrent operations")
    parser.add_argument("-p", "--port", type=int, default=4028)
    parser.add_argument("command")
    parser.add_argument("extra", nargs="*")


@cli.cli(add_arguments)
async def main(args: argparse.Namespace):
    addresses = utils.load_ips_from_csv(args.config, port=args.port)
    for result in await utils.launch(addresses, utils.rexec, args.command, args.extra, batch=args.batch):
        print(f"{repr(result)}")


if __name__ == "__main__":
    asyncio.run(main())
```
