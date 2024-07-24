# Develop

These are instructions for developers, to quickly start coding for `luxos`.


## Pre-requisites
There are essentially three pre-requisites.

### install a recent version of python (eg. >=3.10)
Please check the output of:
```bash
$> python3 --version
Python 3.12.3
```

### cloned code
Code is from a **github checkout**:
```bash
git clone https://github.com/LuxorLabs/luxos-tooling.git
```

### right current working directory
Also we assume **the current directory is the check out directory**:
```bash
cd luxos-tooling
```

## Setup

First you need to [create the python virtual environment](#create-the-python-virtual-environment) and 
[setting up the repository](#setting-up-the-repository): these two steps need to be done only once.


### create the python virtual environment

First you need to create a virtual environment and install all dependencies:

::::{tabs}
:::{tab} Windows
```shell
python3 -m venv %CD%\venv
.\venv\Scripts\activate.bat    

%CD%\venv\Scripts\pip install -r tests\requirements.txt
%CD%\venv\Scripts\pip install -e .
```
:::
:::{tab} *NIX
```bash
python3 -m venv $(pwd)/venv  
source ./venv/bin/activate

./venv/bin/pip install -r tests\requirements.txt
./venv/bin/pip install -e .
```
:::
::::

### Setting up the repository

Luxos leverages [pre-commit](https://pre-commit.com/) to execute
checks on code commit, so the code can be checked for issues before being
submitted to the repo.

::::{tabs}
:::{tab} Windows
```bash
%CD%\venv\Scripts\pre-commit install
```
:::
:::{tab} *NIX
```bash
./venv/bin/pre-commit install
```
:::
::::



## Coding

To begin coding, you first have to [activate the virtual environment](#activate-the-virtual-environment):
this steps has to be followed every time you restart the shell/cmd.

### activate the virtual environment

Every time you start a new shell, you need to activate the environment: this
will set the correct **PATH**.

::::{tabs}
:::{tab} Windows
```shell
.\venv\Scripts\activate
```
:::
:::{tab} Windows (powershell)
```shell

.\venv\Scripts\activate.ps1
```
:::
:::{tab} *NIX
```shell
source ./venv/bin/activate
```
:::
::::
 

### run tests
To run all (unit) tests:
```shell
pytest -vvs tests
```

To run tests (including non units):
```shell
pytest -vvs --manual tests
```

To run all tests targeting a miner (eg. 127.0.0.1):
```shell
MINER=127.0.0.1 pytest -vvs --manual tests
```

To restrict the run to a single test:
```shell
pytest -vvs  tests --manual -k "test_utils.py"
```
(`-k` takes wildcards).


:::{tip}
You can generate coverage and junit html document using:
```shell
make tests MINER=127.0.0.1
```
:::

### commit (eg. pre-commit hooks)
To guarantee code quality, you can leverage [pre-commit](https://pre-commit.com/) hooks
to help you validate code at every git commit (as done in [Setting up the repository](setting-up-the-repository)).

All you need to do is:
```shell
git commit ...
```

If for any reason you want disable the hooks, use the `-n` flag to git commit:
```shell
git commit -n ...
```

:::{note}
At every `git commit` pre-commit will run for you:
- [ruff](https://github.com/astral-sh/ruff) for static code check
- [mypy](https://mypy-lang.org) for static typing checks
:::
