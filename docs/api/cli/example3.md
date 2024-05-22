# examples3

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


