# LuxOS Tools Repository

[![PyPI version](https://img.shields.io/pypi/v/luxos.svg?color=blue)](https://pypi.org/project/luxos)
[![Python versions](https://img.shields.io/pypi/pyversions/luxos.svg)](https://pypi.org/project/luxos)
[![License - MIT](https://img.shields.io/badge/license-MIT-9400d3.svg)](https://spdx.org/licenses/)
[![Build](https://github.com/LuxorLabs/luxos-tooling/actions/workflows/push-main.yml/badge.svg)](https://github.com/LuxorLabs/luxos/actions/runs/0)
![PyPI - Downloads](https://img.shields.io/pypi/dm/luxos)
[![Mypy](https://img.shields.io/badge/types-Mypy-blue.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This repository contains scripts we built to operate and troubleshoot miners running LuxOS.

For an example how to use the luxos command line tool 👉 [here](#usage-cli).

For a quick example how to control miners using the luxos api 👉 [here](#usage-api).

If you're developing a script, you might want to leverage the luxos cli package 👉 [here](docs/api/cli.md).

## Quick scripting examples

### launch a single command
This will launch the version command on a single miner, returning the json output:
```shell
luxos --range 127.0.0.1 --cmd version
```
You can pass a "range" of ips:
```shell
luxos --range 127.0.0.1:127.0.0.4 --cmd version
```
Or you can save them in a csv file:
```shell
luxos --range @miners.csv --cmd version
```

### launch a script on multiple miner
The `luxos-run` allow to "*run*" a script on miners:

```shell
luxos-run --range 127.0.0.1 my-script.py
```
(note the syntax is similar to luxos)

The `my-script.py` file look like:
```python
from luxos import asyncops
async def main(host: str, port: int):
    res = await asyncops.rexec(host, port, "version")
    return asyncops.validate(host, port, res, "VERSION")[0]
```


## Installation

To install the latest and greatest version:
```bash
   $> pip install -U luxos
```

To install a beta (see [here](https://pypi.org/project/luxos/#history) for the complete list):
```bash
   $> pip install -U luxos==0.0.5b18
```

Finally you can install the latest bleeding edge code as:
```bash
   $> pip install git+https://github.com/LuxorLabs/luxos-tooling.git
```

If you're new to a python `venv`, there are generic instructions [venv](https://docs.python.org/3/library/venv.html).

## Verify

Once installed you can verify the version and the commit the code is from using:
```bash
   $> python -c "import luxos; print(luxos.__version__, luxos.__hash__)"
   0.0.5 08cc733ce8aedf406856c8ad9ccbe44e78917a37
```

## Help

See files under the docs/folder.


## Examples
This is a curated list of examples.

### Usage (api)

You can use the python api to perform the commands instead the CLI.

This is way to get version data from a miner (async version):
```python

   >>> from luxos.asyncops import rexec, validate
   >>> res = await rexec("127.0.0.1", 4028, "version")
   {'STATUS': [{'Code': 22, 'Description': 'LUXminer ...
   >>> validate(res, "VERSION")
   {'API': '3.7', ...
```

There's a syncronous version, with identical calling conventions:
```python

   >>> from luxos.syncops import rexec, validate
   >>> res = rexec("127.0.0.1", 4028, "version")
   {'STATUS': [{'Code': 22, 'Description': 'LUXminer ...
   >>> validate(res, "VERSION")
   {'API': '3.7', ...
```


Alternatively, you can use the module `utils`, where there are support functions for one-shot command execution:

```python
   >>> import asyncio
   >>> from luxos import utils
   >>> asyncio.run(utils.rexec("127.0.0.1", 4028, "vesion"))
   {'STATUS': [{'Code': 22, 'Description': 'LUXminer ...
```
`rexec` has a nicer api and it takes care of formatting the parameters, the full signature is:
```python
rexec(host="127.0.0.1", port=4028, cmd="version", parameters="", timeout=2., retry=1, retry_delay=3.)
```
Where `parameters` can be a string a list of any type (it will be converted into a str) or a dictionary (same conversion to string will apply).
timeout is the timeout for a call, retry is the number of try before giving up, and retry_delay controls the delay between retry.

The `luxos.utils.lauch` allows to rexec commands to a list of miners stored in a file:

```python
   >>> import asyncio
   >>> from luxos import utils
   >>> async def task(host: str, port: int):                   # task must be a callable 
   ...   return await utils.rexec(host, port, "version")
   >>> addresses = utils.load_ips_from_csv("miners.csv")       # miners.csv contains a list of ip addresses, one per line
   >>> asyncio.run(utils.launch(addresses, task, batch=None))  # batched is a keyword argument to limit execution rate (if set to a positive int)
   [{'STATUS': [{'Code': 22, 'Description': 'LUXmin ....

   OR in one line:
   >>> asyncio.run(utils.launch(addresses, utils.rexec, "version", batch=None))
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
