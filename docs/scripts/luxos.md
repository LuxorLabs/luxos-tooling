# `luxos` command line tool

```{toctree}
:maxdepth: 2

recipes
```

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

