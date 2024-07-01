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
api/cli.md
api/utils.md
api/luxos.rst
```


# Welcome to Luxos tooling

## Intro

The luxos python package provides:

1. A simple script `luxos`, allowing to run a single command on miners
2. A script `luxos-run` able to run scriptlets on miners
3. A consistent API to access miners functionality through the the luxos python package (eg. `import luxos`)


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

## Quick start

### Using the `luxos` command line tool

The [luxos](https://pypi.org/project/luxos) python package comes with a command line script 
called `luxos`: it can issue a command (with parameters) to a list of miners' ips
in a csv file.

This will enquire a list of miners for their version:
```bash
   $> luxos --ipfile miners.csv --timeout 2 --quiet --cmd version
   > 10.206.1.152:4028
   | {
   |   "STATUS": [
   |     {
   |       "Code": 22,
   |       "Description": "LUXminer 2024.6.18.181313-3afaf1f",
   |       "Msg": "LUXminer versions",  
```

> **NOTE** 
> 1. instead `--ipfile` you can also use the `--range` flag: it can
> take addresses like `127.0.0.1`, ranges as `127.0.0.1-127.0.0.5` or filenames
> as `@miners.csv`.
> 2. you can use the `--json` to save the results in json format (to stdout).

### Using the `luxos-run` command line tool

The `luxos-run` allows to run as **scriptlet** (a small python script) targeting miners:
a scriptlet usually can contain some logic and or longer commands.

**hello-world.py** scriplet:
```python
from luxos import asyncops

async def main(host: str, port: int):
    # async sending to the miner the version command
    res = await asyncops.rexec(host, port, "version")

    # validate will check the message is correct and return the result
    return asyncops.validate(res, "VERSION", 1, 1)
```

Running the `luxos-run` will execute the scriptlet aggregating the results in
a dictionary with key set to the miner address:
```bash
   $> luxos-run --range @miners.csv --quiet --json hello-world.py
   {
     "10.206.1.152:4028": {
       "API": "3.7",
       "CompileTime": "Tue Jun 18 18:19:10 UTC 2024",
       "LUXminer": "2024.6.18.181313-3afaf1f",
       "Miner": "2024.6.18.181313",
       "Type": "Antminer S19 XP"
     },
     "10.206.1.153:4028": {
       "API": "3.7",
     ...
````

### The python api

[luxos](https://pypi.org/project/luxos) python package comes with an API to support 
miners operations. The main fuctions are stored in the `luxos.util` module for
convenience and they are:
- **rexec** - an async function to send a single command to a miner and return
- **launch** - an async function to bacth execute a callbe targeting miners
- **load_ips_from_csv** - to load miners addresses from a csv file

#### the rexec function
The `rexec` function allows to send a command to a miner and return the response:
```python
   
    from luxos import utils
    res = utils.asyncio.run(utils.rexec("10.206.0.157", 4028, "version"))
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

# execute task across all miners, batch will limit execution rate to 4
asyncio.run(utils.launch(addresses, task, batch=4))

# a one liner
asyncio.run(utils.launch(addresses, lambda h, p: utils.rexec(h, p, "version"), batch=None))
```


