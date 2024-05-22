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

The luxos tooling provides:

1. A consistent API to access miners functionality through the the luxos python package (eg. `import luxos`)
2. A bunch of utility cli scripts to help everyday maintenance (`luxos` and `health-checker` at the moment)


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

### Using the comman line tool `luxos`

The [luxos](https://pypi.org/project/luxos) python package comes with a 
command line script called `luxos`: it can issue a command (with parameters) to a list of miners' ips
in a csv file.

This will enquire a list of miners for their version:
```bash
   $> luxos --ipfile miners.csv --timeout 2 --async --all --cmd version
   > 10.206.1.153:4028
   | {
   |   "STATUS": [
   |     {
   |       "Code": 22,
   |       "Description": "LUXminer 2024.5.1.155432-f2badc0f",
```

### Using the python api

[luxos](https://pypi.org/project/luxos) python package comes with an API to support 
miners operations.

This is way to get version data from a single miner using the API:
```python

   >>> from luxos.utils import execute_command
   >>> execute_command("127.0.0.1", 4028, 2, "version", "", False)
   {'STATUS': [{'Code': 22, 'Description': 'LUXminer ...
```

There's also an async version:
```python
   >>> import asyncio
   >>> from luxos import utils
   >>> asyncio.run(utils.rexec("127.0.0.1", 4028, "vesion"))
   {'STATUS': [{'Code': 22, 'Description': 'LUXminer ...
```
`rexec` takes care of formatting the parameters also, the full signature is:
```python
rexec(
    host="127.0.0.1", port=4028, 
    cmd="version", parameters="",
    timeout=2., retry=1, retry_delay=3.)
```
`parameters` can be a string, a list of any type (it will be converted into a str) or a dictionary (same conversion to string will apply).  `timeout` is the timeout for a call `retry` is the number of try before giving up `retry_delay` controls the delay between retry.

#### launch
The `luxos.utils.lauch` allows to rexec commands to a list of miners stored in a csv file.
This all-in-one function, allows batched operations on a set of miners, taking care of all details.

```python
   >>> import asyncio
   >>> from luxos import utils

   # load miners addresses from miners.csv
   >>> miners = utils.load_ips_from_csv("miners.csv")


   # define a task with (host, port) signature, acting on a miner
   >>> async def task(host: str, port: int):
   ...   return await utils.rexec(host, port, "version")


   # execute task across all miners, batched will limit execution rate
   >>> asyncio.run(utils.launch(addresses, task, batch=None))
   [{'STATUS': [{'Code': 22, 'Description': 'LUXmin ....

   # the one-liner for the version command
   >>> asyncio.run(utils.launch(addresses, utils.rexec, "version", batch=None))
```


