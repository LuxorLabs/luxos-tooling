# basic usage (logging)
[download](_static/simple1.py)

This is the most basic cli script, showing the basics.

```python
... hidden code

import luxos.cli.v1 as cli

# this is the default, here just to show usage
LOGGING_CONFIG = {
    'level': logging.INFO,  # This is the default
}

log = logging.getLogger(__name__)

@cli.cli()
def main(args: argparse.Namespace):
    log.debug("a debug message, need to use -v|--verbose to display it")
    log.info("an info message, you can silence it with -q|--quiet")
    log.warning("a warning!")

if __name__ == "__main__":
    main()
```

The `cli.cli` decorator, adds by default two flags to control the logging
printed: `-v|--verbose` to increase the verbosity and `-q|--quiet`.

:::{note}
- the `cli.cli` decorator, adds by default two flags 
  to control the logging printed and takes the `--help` from the script `__doc__`
- the `args` (argparse.Namespace instance) contains two special attributes:
    - `error` is a callable that aborts the script with an error message
    - `modules` contains a list modules leading to the script itself
- `LOGGING_CONFIG` is a dictionary allowing configure the logging from the script itself
:::

## examples (--quiet)

So this will display only the warning level messages:
```shell
simple1.py --quiet

2024-07-25 18:57:12,311 [W] __main__: a warning!
```

## examples (no flags)

By default if no `--verbose`/`--quiet` flag is passed, the logging will display INFO 
level messages (you can change it setting a different `LOGGING_CONFIG` value).
```shell
simple1.py

2024-07-25 19:39:15,204 [I] luxos.cli.v1: py[3.12.3], luxos[/]
2024-07-25 19:39:15,204 [I] __main__: an info message, you can silence it with -q|--quiet
2024-07-25 19:39:15,204 [W] __main__: a warning!
...
2024-07-25 19:39:15,204 [I] luxos.cli.v1: task completed in 0.00s
```

## examples (--verbose)

```shell
simple1.py --verbose

2024-07-25 19:42:18,674 [I] luxos.cli.v1: py[3.12.3], luxos[/]
2024-07-25 19:42:18,674 [D] luxos.cli.v1: interpreter: /Users/antonio/venvs/luxos-tooling/bin/python
2024-07-25 19:42:18,674 [D] luxos.cli.v1: version: 3.12.3 (v3.12.3:f6650f9ad7, Apr  9 2024, 08:18:47) [Clang 13.0.0 (clang-1300.0.29.30)]
2024-07-25 19:42:18,674 [D] __main__: a debug message, need to use -v|--verbose to display it
2024-07-25 19:42:18,674 [I] __main__: an info message, you can silence it with -q|--quiet
2024-07-25 19:42:18,674 [W] __main__: a warning!
...
2024-07-25 19:42:18,674 [I] luxos.cli.v1: task completed in 0.00s
```