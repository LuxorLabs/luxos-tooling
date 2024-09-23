% THIS IS COMMONMARK, NOT MARKDOWN
% SEE https://myst-parser.readthedocs.io/en/latest
```{toctree}
:hidden:
:maxdepth: 2
:caption: Getting Started

installation
develop
```

```{toctree}
:hidden:
:maxdepth: 2
:caption: Scripts

scripts/luxos.md


```

```{toctree}
:hidden:
:maxdepth: 2
:caption: API

api.md
api/examples.md
api/cli.md
api/utils.md
api/luxos.rst
```


# Welcome to Luxos tooling

## Intro

The [luxos](https://pypi.org/project/luxos) python package provides:

1. A cli script `luxos`, allowing to run a single command on miners
2. A script `luxos-run` to run scriptlets on miners in parallel (using asyncio)
3. A consistent API to access miners functionality through the the `luxos` python package

For simple to follow example on how to use the API see [here](api-examples)

## Install

Detailed instruction on how to install it are provided  👉 [here](installation), to install the latest released code:

```bash
# to install it
$> pip install luxos

# to upgrade it
$> pip install --upgrade luxos

# to verify the current version
$> python -c "import luxos; print(luxos.__version__, luxos.__hash__)"
0.0.7 27e53c7b37ac1bbb88112f3c931b9cd8f1a74a3a
```

## `luxos` command line tool

The [luxos](https://pypi.org/project/luxos) python package comes with a command line script 
called `luxos`: it can issue a command (with parameters) to a list of miners' ips
in a csv file.

This will launch the version command on a miner, returning the json output:
```shell
luxos --range 127.0.0.1 --quiet --json --cmd version 
```
The `--range` flag can take:
* a single ip address, eg: `--range 127.0.0.1`
* a range like: `--range 127.0.0.1-127.0.0.5` 
* or addresses from a file: `--range @miners.csv`.

Other examples:

```shell
# set/unset ATM
luxos --range 127.0.0.1 --quiet --json --cmd atmset --params "enabled=true"

# add a new profile
luxos --range 127.0.0.1 --quiet --json --cmd profilenew --params "myprofile,700,14.8"
```

> **NOTE** 
> 1. `--ipfile` is an alternative way to load miners from a csv file, it's the same as `--range` flag: it can
> take addresses like `127.0.0.1`, ranges as `127.0.0.1-127.0.0.5` or filenames
> as `@miners.csv`.
> 2. you can use the `--json` to save the results in json format (to stdout).

## `luxos-run` command line tool

The `luxos-run` is an alternative to `luxos` command line script, 
allowing to run as **scriptlet** (a small python script) targeting miners:
a scriptlet usually can contain some logic and or longer commands sequences.

**hello-world.py** scriplet:
```python
from luxos import asyncops

async def main(host: str, port: int):
    # async sending to the miner the version command
    res = await asyncops.rexec(host, port, "version")

    # validate will check the message is correct and return the result
    version = asyncops.validate(res, "VERSION", 1, 1)
    return {"address": f"{host}:{port}", "miner": version["LUXminer"]}
```

Running the `luxos-run` will execute the scriptlet aggregating the results in
a dictionary with key set to the miner address:
```bash
luxos-run --range @miners.csv --quiet --json hello-world.py
{
  "127.0.0.1:4028": {
    "address": "127.0.0.1:4028",
    "version": "2021.1.12.202305-nnnn"
  }
}
````

## The python api

[luxos](https://pypi.org/project/luxos) python package comes with an API to support 
miners operations. The main fuctions are stored in the [](luxos.utils) module for
convenience and they are:
- [luxos.util.load_ips_from_csv](luxos.ips.load_ips_from_csv) - utility to load miners addresses from a CSV file
- [luxos.util.rexec](luxos.asyncops.rexec) - an async function to launch commands on a miner
- [luxos.util.execute_command](luxos.syncops.execute_command) - the syncronous `rexec` version
- [luxos.util.validate](luxos.asyncops.validate) - validate a message from a miner
- [luxos.util.launch](luxos.utils.launch) - run a command on multiple miners


#### the rexec function
The `rexec` function allows to send a command to a miner and return the response:
```python
   
    from luxos import utils
    res = utils.asyncio.run(utils.rexec("127.0.0.1", 4028, "version"))
    # this is the validate helper
    print(utils.validate(res, "VERSION", 1, 1))
```

The full signature for `rexec` takes care of formatting the parameters, the full signature is:
```python
rexec(
    host="127.0.0.1", port=4028, 
    cmd="version", parameters="",
    timeout=2., retry=1, retry_delay=3.)
```
`parameters` can be a string, a list of any type (it will be converted into a str) 
or a dictionary (same conversion to string will apply).  

`timeout` is the timeout for a call `retry` is the number of try 
before giving up `retry_delay` controls the delay between retry.

> **NOTE** `rexec` is an async function, 
> but there's a sync version under `luxos.syncops.rexec`.

#### launch
The `luxos.utils.lauch` allows to rexec commands to a list of miners stored in a csv file.
This all-in-one function, allows batched operations on a set of miners, taking care of all details.

```python
import asyncio
from luxos import utils

# load miners addresses from miners.csv
addresses = utils.load_ips_from_csv("miners.csv")


# define a task with (host, port) signature, acting on a miner
async def task(host: str, port: int):
    return await utils.rexec(host, port, "version")

# execute 'task' on miners addresses, targeting 4 miners simultaneous
# (eg. for larger batches utils.launch will finish earlier)
asyncio.run(utils.launch(addresses, task, batch=4))

# a one liner-ish
version = functools.partial(utils.rexec, cmd="version")
asyncio.run(utils.launch(addresses, version, batch=None))
```
