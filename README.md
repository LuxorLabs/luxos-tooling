# LuxOS Tools Repository

[![PyPI version](https://img.shields.io/pypi/v/luxos.svg?color=blue)](https://pypi.org/project/luxos)
[![Python versions](https://img.shields.io/pypi/pyversions/luxos.svg)](https://pypi.org/project/luxos)
[![License - MIT](https://img.shields.io/badge/license-MIT-9400d3.svg)](https://spdx.org/licenses/)
[![Build](https://github.com/LuxorLabs/luxos-tooling/actions/workflows/push-main.yml/badge.svg)](https://github.com/LuxorLabs/luxos/actions/runs/0)
![PyPI - Downloads](https://img.shields.io/pypi/dm/luxos)
[![Mypy](https://img.shields.io/badge/types-Mypy-blue.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This package contains the `luxos` python package: a collection of scripts and api to operate miners running LuxOS. See the
full documentation [here](https://luxorlabs.github.io/luxos-tooling).

## Install

To install the latest version:
```bash
   $> pip install -U luxos

   # to install the extra features
   $> pip install -U luxos[extra]
```

You can check the version:
```bash
python -c "import luxos.version; print(luxos.version.get_version())"
py[3.13.0rc2], luxos[0.2.4, 08cc733ce]
```

## Api usage

### rexec/validate

The [luxos](https://pypi.org/project/luxos) has an extremely simple api.

For example to retrive the version info from a miner:
```
import asyncio
from luxos.asyncops import rexec, validate

# for a miner at 127.0.0.1 listening to port 4028 (the default)
res = await rexec("127.0.0.1", 4028, "version")
print(validate(res, "VERSION", 1, 1))

{'API': '3.7', 'CompileTime': 'Tue Sep 17 17:49:18 UTC 2024', 'LUXminer': '2024.9.17.174900-4631c4d1', 'Miner': '2024.9.17.174900', 'Type': 'Antminer S19'}
```
> **NOTE** The above should be executed using `python3 -m asyncio` instead `python3`.

For a syncronous version (eg. not using asyncio):
```
import asyncio
from luxos.syncops import rexec, validate
res = rexec("127.0.0.1", 4028, "version")
print(validate(res, "VERSION", 1, 1))  # validate makes sure you the correct message and returns one dictionary
```
Yes, it only needs to import `luxos.syncops` instead `luxos.asyncops`, the api is similar (minus the async/await).

> **NOTE** the [rexec](https://luxorlabs.github.io/luxos-tooling/api/luxos.asyncops.html#luxos.asyncops.rexec) function supports also
timeouts and retry.
> The [validate](https://luxorlabs.github.io/luxos-tooling/api/luxos.asyncops.html#luxos.asyncops.validate) check the result.

## Scripting

[luxos](https://pypi.org/project/luxos) comes with some helper
scripts, to ease everyday miners' maintenance.

### luxos (cli)

This will launch the version command on a miner, returning the json output:
```shell
luxos --range 127.0.0.1 --quiet --json --cmd version 
```
The `--range` flag can tak as argument:
* a single ip address `--range 127.0.0.1`
* a range like `--range 127.0.0.1-127.0.0.5` 
* or addresses from a file `--range @miners.csv`.

Other examples:

```shell
# set/unset ATM
luxos --range 127.0.0.1 --quiet --json --cmd atmset --params "enabled=true"

# add a new profile
luxos --range 127.0.0.1 --quiet --json --cmd profilenew --params "myprofile,700,14.8"
```

### luxos-run (cli)
The `luxos-run` allow to "*run*" a scriptlet on miners.

A scriptlet is a a python file such as `my-script.py` looking like this:
```python
from luxos import asyncops
async def main(host: str, port: int):
    res = await asyncops.rexec(host, port, "version")
    return asyncops.validate(host, port, res, "VERSION")[0]
```
The `main` entry point is an async function, taking **host**, **ip** parameter: they
can execute more complex operations on a set of miners specified with the
`--range` flag, in the same way the `luxos` cli script does.

This will run `my-script.py` and report the results in json:
```shell
luxos-run --range 127.0.0.1 my-script.py
```

## API

[luxos](https://pypi.org/project/luxos) provides an easy-to-use API to
write complex scripts on miners.

It comes in two different flavours, a sync version for legacy non high performance
operations, and an async version allowing operation on a fleet of miners: the API
of the main functions is essentially keep identical.

### Main functions

The whole of the "*kernel*" API is rather small-ish and it is based 
essentially on few functions:
- **luxos.utils.load_ips_from_csv** - utility to load miners addresses from a CSV file
- **luxos.utils.rexec** - an async function to launch commands on a miner
- **luxos.utils.execute_command** - the same as rexec but syncronous
- **luxos.utils.validate** - validate a message from a miner
- **luxos.utils.launch** - run a command on multiple miners

[Full documentation](https://luxorlabs.github.io/luxos-tooling).

### Get a miner's version (example)

Get a miner's version data (async version):
```python
import asyncio
from luxos.utils import rexec, validate

async def get_version(host: str, port: int) -> dict:
    res = await rexec(host, port, "version")
    return validate(res, "VERSION", 1, 1)

if __name__ == "__main__":
    print(asyncio.run(get_version("127.0.0.1", 4028)))
```

There's a syncronous version (better for one-liners), with identical calling conventions:
```python
from luxos.utils import execute_command, validate, load_ips_from_csv

if __name__ == "__main__":
    print(validate(execute_command(
        "127.0.0.1", 4028, 3, "version"), "VERSION", 1, 1))
```


### Run commands  (example)

The `luxos.utils.launch` is an async function to launch a command on a
set of miners using asyncio.

This is a simple example (see [Full documentation](https://luxorlabs.github.io/luxos-tooling))
for more.

```python
import asyncio
from luxos.utils import validate, load_ips_from_csv, rexec, launch

async def get_version(host: str, port: int) -> dict:
    res = await rexec(host, port, "version")
    return validate(res, "VERSION", 1, 1)

if __name__ == "__main__":
    addresses = load_ips_from_csv("miners.csv")
    print(asyncio.run(launch(addresses, get_version)))
```

## LuxOS HealthChecker - health_checker.py

The HealthChecker script is designed to continuously pull miner data from LuxOS, providing valuable insights into the health of your mining machines.

You can customize the HealthChecker params using the `config.yaml` file provided. 
To run the HealthChecker you can use `health-checker` if you installed using pip, or
the cli `python3 -m luxos.scripts.health_checker`.

---

Feel free to explore and customize these tools to suit your specific needs. 
If you encounter any issues or have suggestions for improvement, please open an issue or submit a pull request.

You can find LuxOS API documentation [here](https://docs.luxor.tech/firmware/api/intro).
